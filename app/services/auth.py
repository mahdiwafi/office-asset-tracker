# app/services/auth.py
# Entra ID JWT verification. The trust chain in one function: prove the
# token was written by the holder of the tenant's private key (via the
# public keys published in the JWKS), then check the claims that bind it
# to our app and to the current time.

import base64
import datetime
import json

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.config import settings
from app.services.errors import TokenExpiredError, TokenInvalidError

# One fetch per process: Azure rotates signing keys rarely (weeks), and
# every token in this window verifies against the same set. Tests reset
# this and stub _fetch_jwks.
_jwks_cache: dict | None = None

# Grace window for clock drift between this server and the token issuer.
CLOCK_SKEW_SECONDS = 30


def _b64url_decode(part: str) -> bytes:
	return base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))


def _issuer() -> str:
	return f'https://login.microsoftonline.com/{settings.entra_tenant_id}/v2.0'


def _jwks_url() -> str:
	return (
		f'https://login.microsoftonline.com/{settings.entra_tenant_id}'
		'/discovery/v2.0/keys'
	)


async def _fetch_jwks() -> dict:
	async with httpx.AsyncClient() as client:
		response = await client.get(_jwks_url())
		response.raise_for_status()
		return response.json()


async def _jwks() -> dict:
	global _jwks_cache
	if _jwks_cache is None:
		_jwks_cache = await _fetch_jwks()
	return _jwks_cache


def _public_key(key_json: dict) -> rsa.RSAPublicKey:
	# JWKS keys ship n and e as base64url-encoded big-endian integers.
	exponent: int = int.from_bytes(_b64url_decode(key_json['e']), 'big')
	modulus: int = int.from_bytes(_b64url_decode(key_json['n']), 'big')
	return rsa.RSAPublicNumbers(exponent, modulus).public_key()


async def verify_token(token: str) -> dict:
	if not settings.entra_tenant_id or not settings.entra_client_id:
		raise TokenInvalidError('Entra ID is not configured')

	parts = token.split('.')
	if len(parts) != 3:
		raise TokenInvalidError('token is not a JWT')
	header_b64, payload_b64, signature_b64 = parts
	try:
		header: dict = json.loads(_b64url_decode(header_b64))
		payload: dict = json.loads(_b64url_decode(payload_b64))
	except (ValueError, json.JSONDecodeError):
		raise TokenInvalidError('token header or payload is not valid JSON') from None

	if header.get('alg') != 'RS256':
		# Algorithm confusion guard: alg=none or a symmetric algorithm
		# would let anyone forge a token using our public key as the
		# shared secret. Pin the asymmetric algorithm.
		raise TokenInvalidError(f'unsupported algorithm {header.get("alg")!r}')

	key_json = next(
		(
			key
			for key in (await _jwks()).get('keys', [])
			if key.get('kid') == header.get('kid')
		),
		None,
	)
	if key_json is None:
		raise TokenInvalidError(f'no JWKS key for kid {header.get("kid")!r}')

	# The signature covers the untouched header.payload bytes. Any edit to
	# either segment breaks the match. InvalidSignature is a ValueError.
	signing_input = f'{header_b64}.{payload_b64}'
	try:
		_public_key(key_json).verify(
			_b64url_decode(signature_b64),
			signing_input.encode(),
			padding.PKCS1v15(),
			hashes.SHA256(),
		)
	except InvalidSignature:
		raise TokenInvalidError('signature verification failed') from None

	now: float = datetime.datetime.now(datetime.UTC).timestamp()
	exp: int | None = payload.get('exp')
	nbf: int | None = payload.get('nbf')
	if exp is None or now > exp + CLOCK_SKEW_SECONDS:
		raise TokenExpiredError('token is expired')
	if nbf is not None and now < nbf - CLOCK_SKEW_SECONDS:
		raise TokenExpiredError('token is not yet valid')

	if payload.get('aud') not in (settings.entra_client_id, settings.api_audience):
		# The SPA's token for the exposed API scope carries the Application
		# ID URI as its audience; a token for the client itself carries the
		# GUID. Either is this app — anything else is a token for someone
		# else's API.
		raise TokenInvalidError(
			f'token audience {payload.get("aud")!r} does not match this app'
		)
	if payload.get('iss') != _issuer():
		raise TokenInvalidError(
			f'token issuer {payload.get("iss")!r} does not match this tenant'
		)
	return payload
