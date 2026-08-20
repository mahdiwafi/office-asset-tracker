# tests/test_api.py

import datetime

import sqlalchemy

from app.models import (
	Asset,
	AuditEvent,
	Category,
	Loan,
	LoanCondition,
	Request,
	RequestStatus,
	User,
	UserRole,
)
from tests.token_helpers import base_payload, mint_token

# Every request runs through the real ASGI app (api_client fixture) on one
# per-test transaction that rolls back at teardown. Seeds and assertions go
# through the fixture's session — never a fresh one. Identity comes from
# bearer tokens minted with the demo keypair (bearer_headers fixture);
# each test seeds a user with the same Entra object id, or relies on
# first-login provisioning.

TODAY: datetime.date = datetime.date.today()

_oid_counter: int = 0


def _next_oid() -> str:
	global _oid_counter
	_oid_counter += 1
	return f'11111111-1111-1111-1111-{_oid_counter:012d}'


def _iso(days_from_today: int) -> str:
	return (TODAY + datetime.timedelta(days=days_from_today)).isoformat()


async def _seed_user(session, email: str, role: UserRole, entra_oid: str) -> int:
	user: User = User(
		email=email, name=email.split('@')[0], role=role, entra_oid=entra_oid
	)
	session.add(user)
	await session.flush()
	return user.id


async def _seed_category(session) -> int:
	category: Category = Category(name='http-laptop')
	session.add(category)
	await session.flush()
	return category.id


async def _seed_asset(session, category_id: int, tag: str) -> int:
	asset: Asset = Asset(
		inventory_tag=tag, name='MacBook Pro 14', category_id=category_id
	)
	session.add(asset)
	await session.flush()
	return asset.id


def _loan_payload(asset_id: int, borrower_id: int) -> dict:
	return {
		'asset_id': asset_id,
		'borrower_id': borrower_id,
		'start_date': _iso(0),
		'due_date': _iso(14),
		'condition_out': 'good',
	}


async def test_create_asset_returns_201_and_persists(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	# The token's oid is seeded so the audit event names a known user.
	# Unseeded oids are provisioned on first login instead (see
	# test_first_request_provisions_user_from_token).
	oid = _next_oid()
	await _seed_user(session, 'http-cataloguer@example.com', UserRole.staff, oid)
	response = await client.post(
		'/assets',
		headers=bearer_headers(oid),
		json={
			'inventory_tag': 'HTTP-ASSET-1',
			'name': 'MacBook Pro 14',
			'category_id': category_id,
			'status': 'available',
			'condition': 'good',
		},
	)
	assert response.status_code == 201
	body = response.json()
	assert body['inventory_tag'] == 'HTTP-ASSET-1'
	asset = await session.get(Asset, body['id'])
	assert asset is not None
	assert asset.name == 'MacBook Pro 14'


async def test_duplicate_inventory_tag_returns_409(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	payload = {
		'inventory_tag': 'HTTP-ASSET-2',
		'name': 'ThinkPad X1',
		'category_id': category_id,
	}
	oid = _next_oid()
	await _seed_user(session, 'http-cataloguer2@example.com', UserRole.staff, oid)
	headers = bearer_headers(oid)
	first = await client.post('/assets', headers=headers, json=payload)
	assert first.status_code == 201
	second = await client.post('/assets', headers=headers, json=payload)
	assert second.status_code == 409
	assert 'inventory tag' in second.json()['detail']


async def test_create_loan_returns_201_and_persists(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-3')
	oid = _next_oid()
	borrower_id = await _seed_user(session, 'http-borrower@example.com', UserRole.staff, oid)
	response = await client.post(
		'/loans',
		headers=bearer_headers(oid),
		json=_loan_payload(asset_id, borrower_id),
	)
	assert response.status_code == 201
	body = response.json()
	assert body['asset_id'] == asset_id
	loan = await session.get(Loan, body['id'])
	assert loan is not None
	assert loan.condition_out is LoanCondition.good


async def test_double_booking_same_asset_returns_409(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-4')
	oid = _next_oid()
	borrower_id = await _seed_user(session, 'http-borrower2@example.com', UserRole.staff, oid)
	headers = bearer_headers(oid)
	payload = _loan_payload(asset_id, borrower_id)
	first = await client.post('/loans', headers=headers, json=payload)
	assert first.status_code == 201
	second = await client.post('/loans', headers=headers, json=payload)
	assert second.status_code == 409
	assert 'already has an active loan' in second.json()['detail']
	# Only the winning loan exists — the loser never reached the DB.
	loans = await session.scalars(
		sqlalchemy.select(Loan).where(Loan.asset_id == asset_id)
	)
	assert len(loans.all()) == 1


async def test_return_loan_without_condition_returns_400(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-5')
	oid = _next_oid()
	borrower_id = await _seed_user(session, 'http-borrower3@example.com', UserRole.staff, oid)
	headers = bearer_headers(oid)
	create = await client.post(
		'/loans', headers=headers, json=_loan_payload(asset_id, borrower_id)
	)
	loan_id = create.json()['id']
	# No body at all: condition_in defaults to None, and the service
	# refuses to accept a return without recording the returned condition.
	response = await client.post(f'/loans/{loan_id}/return', headers=headers)
	assert response.status_code == 400
	assert 'requires recording' in response.json()['detail']
	loan = await session.get(Loan, loan_id)
	assert loan.returned_at is None


async def test_loan_longer_than_30_days_returns_422(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-6')
	oid = _next_oid()
	borrower_id = await _seed_user(session, 'http-borrower4@example.com', UserRole.staff, oid)
	payload = _loan_payload(asset_id, borrower_id)
	payload['due_date'] = _iso(31)
	response = await client.post(
		'/loans', headers=bearer_headers(oid), json=payload
	)
	assert response.status_code == 422
	assert 'exceeds the maximum' in response.json()['detail']


async def test_loan_for_missing_asset_returns_404(api_client, bearer_headers) -> None:
	client, session = api_client
	oid = _next_oid()
	borrower_id = await _seed_user(session, 'http-borrower5@example.com', UserRole.staff, oid)
	payload = _loan_payload(999_999, borrower_id)
	response = await client.post(
		'/loans', headers=bearer_headers(oid), json=payload
	)
	assert response.status_code == 404
	assert 'asset 999999 not found' in response.json()['detail']


async def test_staff_cannot_approve_returns_403(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-7')
	requester_oid = _next_oid()
	await _seed_user(
		session, 'http-requester@example.com', UserRole.staff, requester_oid
	)
	create = await client.post(
		'/requests',
		headers=bearer_headers(requester_oid),
		json={'asset_id': asset_id, 'justification': 'field work'},
	)
	request_id = create.json()['id']
	staff_oid = _next_oid()
	await _seed_user(session, 'http-not-approver@example.com', UserRole.staff, staff_oid)
	response = await client.post(
		f'/requests/{request_id}/decision',
		headers=bearer_headers(staff_oid),
		json={'decision': 'approved'},
	)
	assert response.status_code == 403
	request = await session.get(Request, request_id)
	assert request.status is RequestStatus.pending


async def test_approval_flow_returns_201_and_writes_audit(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-8')
	requester_oid = _next_oid()
	await _seed_user(
		session, 'http-requester2@example.com', UserRole.staff, requester_oid
	)
	approver_oid = _next_oid()
	approver_id = await _seed_user(
		session, 'http-approver@example.com', UserRole.approver, approver_oid
	)
	create = await client.post(
		'/requests',
		headers=bearer_headers(requester_oid),
		json={'asset_id': asset_id, 'justification': 'client visit'},
	)
	request_id = create.json()['id']
	# The token's app roles claim must carry Approver — provisioning
	# mirrors it into the user row the service checks.
	response = await client.post(
		f'/requests/{request_id}/decision',
		headers=bearer_headers(approver_oid, roles=['Approver']),
		json={'decision': 'approved', 'note': 'ok'},
	)
	assert response.status_code == 201
	body = response.json()
	assert body['request_id'] == request_id
	assert body['decision'] == 'approved'
	request = await session.get(Request, request_id)
	assert request.status is RequestStatus.approved
	assert request.decided_at is not None
	# The decision must leave an audit trail visible over HTTP.
	audit = await client.get('/audit', params={'entity_type': 'request'})
	events = [
		event
		for event in audit.json()['items']
		if event['action'] == 'request.decide' and event['entity_id'] == request_id
	]
	assert len(events) == 1
	assert events[0]['actor_id'] == approver_id


async def test_decision_on_missing_request_returns_404(api_client, bearer_headers) -> None:
	client, session = api_client
	oid = _next_oid()
	await _seed_user(session, 'http-approver2@example.com', UserRole.approver, oid)
	response = await client.post(
		'/requests/999999/decision',
		headers=bearer_headers(oid, roles=['Approver']),
		json={'decision': 'approved'},
	)
	assert response.status_code == 404


async def test_loan_list_renders_asset_and_borrower_names(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-9')
	oid = _next_oid()
	borrower_id = await _seed_user(session, 'http-borrower6@example.com', UserRole.staff, oid)
	create = await client.post(
		'/loans',
		headers=bearer_headers(oid),
		json=_loan_payload(asset_id, borrower_id),
	)
	loan_id = create.json()['id']
	# The list joins the asset and borrower names for display, eagerly
	# loaded (selectinload) after the N+1 checkpoint.
	response = await client.get('/loans')
	assert response.status_code == 200
	rows = [row for row in response.json()['items'] if row['id'] == loan_id]
	assert len(rows) == 1
	assert rows[0]['asset_name'] == 'MacBook Pro 14'
	assert rows[0]['borrower_name'] == 'http-borrower6'


async def test_request_creation_is_idempotent_by_key(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-13')
	oid = _next_oid()
	await _seed_user(
		session, 'http-requester3@example.com', UserRole.staff, oid
	)
	headers = {
		**bearer_headers(oid),
		'Idempotency-Key': 'request-create-1',
	}
	payload = {'asset_id': asset_id, 'justification': 'double submission'}
	first = await client.post('/requests', headers=headers, json=payload)
	assert first.status_code == 201
	# The replay returns the original request with 200 — and it must do so
	# before the pending-check would have 409'd on the still-pending row.
	second = await client.post('/requests', headers=headers, json=payload)
	assert second.status_code == 200
	assert second.json()['id'] == first.json()['id']
	requests = await session.scalars(
		sqlalchemy.select(Request).where(Request.asset_id == asset_id)
	)
	assert len(requests.all()) == 1


async def test_loan_list_paginates(api_client, bearer_headers) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_ids = [
		await _seed_asset(session, category_id, f'HTTP-ASSET-{index}')
		for index in range(10, 13)
	]
	oid = _next_oid()
	borrower_id = await _seed_user(session, 'http-borrower7@example.com', UserRole.staff, oid)
	for asset_id in asset_ids:
		await client.post(
			'/loans',
			headers=bearer_headers(oid),
			json=_loan_payload(asset_id, borrower_id),
		)
	page = await client.get('/loans', params={'limit': 2, 'offset': 0})
	assert page.status_code == 200
	body = page.json()
	assert len(body['items']) == 2
	# total counts every loan in the table, including rows committed by
	# other test files — the page only ever carries `limit` rows.
	assert body['total'] >= 3
	assert body['limit'] == 2
	assert body['offset'] == 0


async def test_missing_token_returns_401(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	response = await client.post(
		'/assets',
		json={
			'inventory_tag': 'HTTP-401-1',
			'name': 'MacBook Pro 14',
			'category_id': category_id,
		},
	)
	assert response.status_code == 401
	assert 'missing bearer token' in response.json()['detail']


async def test_garbage_token_returns_401(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	response = await client.post(
		'/assets',
		headers={'Authorization': 'Bearer not-a-token'},
		json={
			'inventory_tag': 'HTTP-401-2',
			'name': 'MacBook Pro 14',
			'category_id': category_id,
		},
	)
	assert response.status_code == 401


async def test_expired_token_returns_401(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	payload = base_payload() | {
		'exp': int(datetime.datetime.now(datetime.UTC).timestamp()) - 3600
	}
	response = await client.post(
		'/assets',
		headers={'Authorization': f'Bearer {mint_token(payload)}'},
		json={
			'inventory_tag': 'HTTP-401-3',
			'name': 'MacBook Pro 14',
			'category_id': category_id,
		},
	)
	assert response.status_code == 401
	assert 'expired' in response.json()['detail']


async def test_first_request_provisions_user_from_token(api_client, bearer_headers) -> None:
	# No user is seeded: the token's oid claim creates the User row on
	# first login, and the audit trail names the provisioned actor.
	client, session = api_client
	category_id = await _seed_category(session)
	oid = _next_oid()
	response = await client.post(
		'/assets',
		headers=bearer_headers(oid),
		json={
			'inventory_tag': 'HTTP-PROV-1',
			'name': 'MacBook Pro 14',
			'category_id': category_id,
		},
	)
	assert response.status_code == 201
	user = await session.scalar(sqlalchemy.select(User).where(User.entra_oid == oid))
	assert user is not None
	assert user.role is UserRole.staff
	event = await session.scalar(
		sqlalchemy.select(AuditEvent).where(AuditEvent.action == 'asset.create')
	)
	assert event.actor_id == user.id
