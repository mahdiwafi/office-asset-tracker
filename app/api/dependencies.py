# app/api/dependencies.py
# The caller's identity: a bearer token from Entra ID. verify_token proves
# the token was signed by the tenant, is bound to this app, and is valid
# now; get_or_create_user maps the oid claim onto a User row, provisioning
# on first login. Any failure raises a TokenInvalidError, which the error
# handler turns into 401 — the caller must authenticate, not that they are
# forbidden (403).

import fastapi
import sqlalchemy.orm as saorm

from app.db import get_db
from app.models import User
from app.services import auth
from app.services.errors import TokenInvalidError
from app.services.users import get_or_create_user


def _bearer_token(authorization: str | None) -> str:
	if not authorization or not authorization.startswith('Bearer '):
		raise TokenInvalidError('missing bearer token')
	return authorization.removeprefix('Bearer ').strip()


async def get_current_user(
	authorization: str | None = fastapi.Header(default=None, alias='Authorization'),
	session: saorm.Session = fastapi.Depends(get_db),
) -> User:
	claims = await auth.verify_token(_bearer_token(authorization))
	return await get_or_create_user(session, claims)
