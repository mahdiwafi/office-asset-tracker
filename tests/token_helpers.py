# tests/token_helpers.py
# Shared JWT machinery for the auth and API tests: mint tokens with the
# FAKE demo keypair (tests/fixtures/*.pem) and build the JWKS response the
# tenant would serve. The issuer/audience must mirror the service's
# computation so tokens verify in both local runs (real .env) and CI
# (empty settings filled in by conftest's _entra_settings fixture).

import base64
import datetime
import json
import pathlib

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.config import settings

FIXTURES = pathlib.Path('tests/fixtures')
OID = '8fc67598-d308-469f-9bc1-f11eaffb0418'
ROLES = ['Staff']
KID = 'demo-key-1'


def b64url(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def load_private_key() -> rsa.RSAPrivateKey:
	return serialization.load_pem_private_key(
		(FIXTURES / 'demo_private_key.pem').read_bytes(), password=None
	)


def load_public_key() -> rsa.RSAPublicKey:
	return serialization.load_pem_public_key(
		(FIXTURES / 'demo_public_key.pem').read_bytes()
	)


def issuer() -> str:
	# One of the tenant's valid issuers (the login.microsoftonline.com
	# form). Tests mint tokens with it; the service also accepts the
	# sts.windows.net form that real access tokens carry.
	return f'https://login.microsoftonline.com/{settings.entra_tenant_id}/v2.0'


def base_payload(*, oid: str = OID, roles: list[str] = ROLES) -> dict:
	now: int = int(datetime.datetime.now(datetime.UTC).timestamp())
	return {
		'iss': issuer(),
		'aud': settings.entra_client_id,
		'exp': now + 3600,
		'nbf': now - 60,
		'iat': now,
		'oid': oid,
		'name': 'Wafi Test',
		'preferred_username': 'wafi.test@prospera.example',
		'roles': roles,
	}


def mint_token(
	payload: dict | None = None,
	*,
	key: rsa.RSAPrivateKey | None = None,
	kid: str = KID,
	alg: str = 'RS256',
) -> str:
	header = {'alg': alg, 'typ': 'JWT', 'kid': kid}
	signing_input = (
		f'{b64url(json.dumps(header).encode())}.'
		f'{b64url(json.dumps(payload or base_payload()).encode())}'
	)
	signer = key or load_private_key()
	signature = signer.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
	return f'{signing_input}.{b64url(signature)}'


def jwks_response() -> dict:
	numbers = load_public_key().public_numbers()
	n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, 'big')
	e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, 'big')
	return {'keys': [{'kty': 'RSA', 'kid': KID, 'n': b64url(n), 'e': b64url(e)}]}
