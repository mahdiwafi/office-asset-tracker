# app/api/dependencies.py

import fastapi


# Pre-auth placeholder: every request acts on behalf of the user id in the
# X-Actor-Id header. Day 4 replaces this with the identity from the
# verified Entra ID token; the shape of the handlers does not change.
def get_actor_id(x_actor_id: int = fastapi.Header()) -> int:
	return x_actor_id
