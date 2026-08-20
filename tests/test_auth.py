# tests/test_auth.py
# JWKS validation: every rejection path, against the fake keypair in
# tests/fixtures. Tokens are minted in-test with the private key; the
# jwks fixture (conftest, autouse) serves the matching public key —
# exactly what a real Entra tenant would serve, minus the network.

import datetime
import json

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import settings
from app.services import auth
from app.services.errors import TokenExpiredError, TokenInvalidError
from tests.token_helpers import OID, b64url, base_payload, mint_token


async def test_valid_token_returns_claims() -> None:
	claims = await auth.verify_token(mint_token())
	assert claims['oid'] == OID
	assert claims['roles'] == ['Staff']
	assert claims['aud'] == settings.entra_client_id


async def test_tampered_payload_rejected() -> None:
	token = mint_token()
	header_b64, _payload_b64, signature_b64 = token.split('.')
	forged_payload = base_payload() | {'roles': ['Admin']}
	forged = (
		f'{header_b64}.{b64url(json.dumps(forged_payload).encode())}.{signature_b64}'
	)
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(forged)


async def test_expired_token_rejected() -> None:
	payload = base_payload() | {
		'exp': int(datetime.datetime.now(datetime.UTC).timestamp()) - 3600
	}
	with pytest.raises(TokenExpiredError):
		await auth.verify_token(mint_token(payload))


async def test_not_yet_valid_token_rejected() -> None:
	payload = base_payload() | {
		'nbf': int(datetime.datetime.now(datetime.UTC).timestamp()) + 3600
	}
	with pytest.raises(TokenExpiredError):
		await auth.verify_token(mint_token(payload))


async def test_missing_exp_rejected() -> None:
	payload = base_payload() | {'exp': None}
	with pytest.raises(TokenExpiredError):
		await auth.verify_token(mint_token(payload))


async def test_wrong_audience_rejected() -> None:
	payload = base_payload() | {'aud': 'some-other-app'}
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(mint_token(payload))


async def test_wrong_issuer_rejected() -> None:
	payload = base_payload() | {'iss': 'https://login.microsoftonline.com/other/v2.0'}
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(mint_token(payload))


async def test_unknown_kid_rejected() -> None:
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(mint_token(kid='not-in-the-jwks'))


async def test_signature_from_unknown_key_rejected() -> None:
	# Same kid, different key: the JWKS finds a key but the signature
	# does not match it.
	other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(mint_token(key=other_key))


@pytest.mark.parametrize(
	('token',),
	[
		('not-a-token',),
		('only.two',),
		('garbage.garbage.garbage',),
	],
)
async def test_garbage_rejected(token: str) -> None:
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(token)


@pytest.mark.parametrize(
	('alg',),
	[
		('none',),
		('HS256',),
	],
)
async def test_algorithm_confusion_rejected(alg: str) -> None:
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(mint_token(alg=alg))


async def test_unconfigured_raises(monkeypatch) -> None:
	monkeypatch.setattr(settings, 'entra_tenant_id', '')
	monkeypatch.setattr(settings, 'entra_client_id', '')
	with pytest.raises(TokenInvalidError):
		await auth.verify_token(mint_token())
