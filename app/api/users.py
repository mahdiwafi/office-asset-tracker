# app/api/users.py
# The signed-in user's own record. The frontend needs the provisioned
# user's database id (for borrower-scoped queries), role, and email.
# /users/me is the one route that answers "who am I" by identity rather
# than by resource.

import fastapi

from app.api.dependencies import get_current_user
from app.models import User
from app.schemas.user import UserRead

router: fastapi.APIRouter = fastapi.APIRouter(prefix='/users', tags=['users'])


@router.get('/me', response_model=UserRead)
async def get_me(
	current_user: User = fastapi.Depends(get_current_user),
) -> User:
	return current_user
