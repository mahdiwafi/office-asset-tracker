# app/services/users.py
# Identity provisioning: Entra is the source of truth for who someone is
# and what role they hold. The verified token's oid claim names a User
# row (entra_oid); first login creates the row, and the token's app roles
# are mirrored into the row's role on every request, so the services that
# check role see exactly what the token said.

import sqlalchemy
import sqlalchemy.orm as saorm

from app.models import User, UserRole
from app.services.errors import TokenInvalidError


def _role_from_claims(claims: dict) -> UserRole:
	token_roles = {str(role).lower() for role in claims.get('roles', [])}
	if 'admin' in token_roles:
		return UserRole.admin
	if 'approver' in token_roles:
		return UserRole.approver
	return UserRole.staff


async def get_or_create_user(session: saorm.Session, claims: dict) -> User:
	oid: str | None = claims.get('oid')
	if not oid:
		raise TokenInvalidError('token is missing the oid claim')

	user: User | None = await session.scalar(
		sqlalchemy.select(User).where(User.entra_oid == oid)
	)
	role: UserRole = _role_from_claims(claims)
	if user is None:
		# First login: provision a row. preferred_username is the Entra
		# email; the fallback keeps the unique email column satisfied for
		# tokens that omit it.
		email: str = claims.get('preferred_username') or f'{oid}@entra.local'
		user = User(
			entra_oid=oid,
			email=email,
			name=claims.get('name') or 'Unknown',
			role=role,
		)
		session.add(user)
	elif user.role is not role:
		# The token is authoritative; keep the row mirroring it.
		user.role = role
	await session.flush()
	return user
