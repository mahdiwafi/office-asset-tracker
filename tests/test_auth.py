# tests/test_auth.py
# JWKS validation: every rejection path, against the fake keypair in
# tests/fixtures. Tokens are minted in-test with the private key; the
# JWKS is stubbed to serve the matching public key — exactly what a real
# Entra tenant would serve, minus the network.

import base64
import datetime
import json
import pathlib

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.config import settings
from app.services import auth
from app.services.errors import TokenExpiredError, TokenInvalidError

FIXTURES = pathlib.Path('tests/fixtures')
OID = '8fc67598-d308-469f-9bc1-f11eaffb0418'


def _b64url(data: bytes) -> str:
	return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _load_private_key() -> rsa.RSAPrivateKey:
	return serialization.load_pem_private_key(
		(FIXTURES / 'demo_private_key.pem').read_bytes(), password=None
	)


def _load_public_key() -> rsa.RSAPublicKey:
	return serialization.load_pem_public_key(
		(FIXTURES / 'demo_public_key.pem').read_bytes()
	)


def _issuer() -> str:
	# Mirrors the service's computation so tests agree with the code in
	# both local runs (real .env) and CI (empty settings).
	return f'https://login.microsoftonline.com/{settings.entra_tenant_id}/v2.0'


def _base_payload() -> dict:
	now: int = int(datetime.datetime.now(datetime.UTC).timestamp())
	return {
		'iss': _issuer(),
		'aud': settings.entra_client_id,
		'exp': now + 3600,
		'nbf': now - 60,
		'iat': now,
		'oid': OID,
		'name': 'Wafi Test',
		'preferred_username': 'wafi.test@prospera.example',
		'roles': ['Staff'],
	}


def _mint(
	payload: dict | None = None,
	*,
	key: rsa.RSAPrivateKey | None = None,
	kid: str = 'demo-key-1',
	alg: str = 'RS256',
) -> str:
	header = {'alg': alg, 'typ': 'JWT', 'kid': kid}
	signing_input = f'{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(payload or _base_payload()).encode())}'
	signer = key or _load_private_key()
	signature = signer.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
	return f'{signing_input}.{_b64url(signature)}'


def _jwks_response() -> dict:
	numbers = _load_public_key().public_numbers()
	n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, 'big')
	e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, 'big')
	return {
		'keys': [
			{'kty': 'RSA', 'kid': 'demo-key-1', 'n': _b64url(n), 'e': _b64url(e)},
		]
	}


@pytest_asyncio.fixture
async def jwks(monkeypatch):
	# Stub the network: serve the demo public key as the tenant's JWKS.
	async def _stub_jwks() -> dict:
		return _jwks_response()

	auth._jwks_cache = None
	monkeypatch.setattr(auth, '_fetch_jwks', _stub_jwks)
	yield
	auth._jwks_cache = None


async def test_valid_token_returns_claims(jwks) -> None:
	claims = await auth.verify_token(_mint())
	assert claims['oid'] == OID
	assert claims['roles'] == ['Staff']
	assert claims['aud'] == settings.entra_client_id


async def test_tampered_payload_rejected(jwks) -> None:
	token = _mint()
	header_b64, _payload_b64, signature_b64 = token.split('.')
	forged_payload = _base_payload() | {'roles': ['Admin']}
	forged = (
		f'{header_b64}.{_b64url(json.dumps(forged_payload).encode())}.{signature_b64}'
	)
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(forged)


async def test_expired_token_rejected(jwks) -> None:
	payload = _base_payload() | {
		'exp': int(datetime.datetime.now(datetime.UTC).timestamp()) - 3600
	}
	with pytest.raises(TokenExpiredError):
		await auth.verify_token(_mint(payload))


async def test_not_yet_valid_token_rejected(jwks) -> None:
	payload = _base_payload() | {
		'nbf': int(datetime.datetime.now(datetime.UTC).timestamp()) + 3600
	}
	with pytest.raises(TokenExpiredError):
		await auth.verify_token(_mint(payload))


async def test_missing_exp_rejected(jwks) -> None:
	payload = _base_payload() | {'exp': None}
	with pytest.raises(TokenExpiredError):
		await auth.verify_token(_mint(payload))


async def test_wrong_audience_rejected(jwks) -> None:
	payload = _base_payload() | {'aud': 'some-other-app'}
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(_mint(payload))


async def test_wrong_issuer_rejected(jwks) -> None:
	payload = _base_payload() | {'iss': 'https://login.microsoftonline.com/other/v2.0'}
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(_mint(payload))


async def test_unknown_kid_rejected(jwks) -> None:
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(_mint(kid='not-in-the-jwks'))


async def test_signature_from_unknown_key_rejected(jwks) -> None:
	# Same kid, different key: the JWKS finds a key but the signature
	# does not match it.
	other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(_mint(key=other_key))


@pytest.mark.parametrize(
	('token',),
	[
		('not-a-token',),
		('only.two',),
		('garbage.garbage.garbage',),
	],
)
async def test_garbage_rejected(jwks, token: str) -> None:
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(token)


@pytest.mark.parametrize(
	('alg',),
	[
		('none',),
		('HS256',),
	],
)
async def test_algorithm_confusion_rejected(jwks, alg: str) -> None:
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(_mint(alg=alg))


async def test_unconfigured_raises(monkeypatch) -> None:
	monkeypatch.setattr(settings, 'entra_tenant_id', '')
	monkeypatch.setattr(settings, 'entra_client_id', '')
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(_mint())
