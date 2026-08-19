# tests/test_api.py

import datetime

import sqlalchemy

from app.models import (
	Asset,
	Category,
	Loan,
	LoanCondition,
	Request,
	RequestStatus,
	User,
	UserRole,
)

# Every request runs through the real ASGI app (api_client fixture) on one
# per-test transaction that rolls back at teardown. Seeds and assertions go
# through the fixture's session — never a fresh one.

TODAY: datetime.date = datetime.date.today()


def _iso(days_from_today: int) -> str:
	return (TODAY + datetime.timedelta(days=days_from_today)).isoformat()


async def _seed_user(session, email: str, role: UserRole) -> int:
	user: User = User(email=email, name=email.split('@')[0], role=role)
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


async def test_create_asset_returns_201_and_persists(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	# The actor header must name a real user: the create writes an audit
	# event whose actor_id is an FK to users.
	actor_id = await _seed_user(session, 'http-cataloguer@example.com', UserRole.staff)
	response = await client.post(
		'/assets',
		headers={'X-Actor-Id': str(actor_id)},
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


async def test_duplicate_inventory_tag_returns_409(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	payload = {
		'inventory_tag': 'HTTP-ASSET-2',
		'name': 'ThinkPad X1',
		'category_id': category_id,
	}
	actor_id = await _seed_user(session, 'http-cataloguer2@example.com', UserRole.staff)
	headers = {'X-Actor-Id': str(actor_id)}
	first = await client.post('/assets', headers=headers, json=payload)
	assert first.status_code == 201
	second = await client.post('/assets', headers=headers, json=payload)
	assert second.status_code == 409
	assert 'inventory tag' in second.json()['detail']


async def test_create_loan_returns_201_and_persists(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-3')
	borrower_id = await _seed_user(session, 'http-borrower@example.com', UserRole.staff)
	response = await client.post(
		'/loans',
		headers={'X-Actor-Id': str(borrower_id)},
		json=_loan_payload(asset_id, borrower_id),
	)
	assert response.status_code == 201
	body = response.json()
	assert body['asset_id'] == asset_id
	loan = await session.get(Loan, body['id'])
	assert loan is not None
	assert loan.condition_out is LoanCondition.good


async def test_double_booking_same_asset_returns_409(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-4')
	borrower_id = await _seed_user(
		session, 'http-borrower2@example.com', UserRole.staff
	)
	headers = {'X-Actor-Id': str(borrower_id)}
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


async def test_return_loan_without_condition_returns_400(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-5')
	borrower_id = await _seed_user(
		session, 'http-borrower3@example.com', UserRole.staff
	)
	headers = {'X-Actor-Id': str(borrower_id)}
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


async def test_loan_longer_than_30_days_returns_422(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-6')
	borrower_id = await _seed_user(
		session, 'http-borrower4@example.com', UserRole.staff
	)
	payload = _loan_payload(asset_id, borrower_id)
	payload['due_date'] = _iso(31)
	response = await client.post(
		'/loans', headers={'X-Actor-Id': str(borrower_id)}, json=payload
	)
	assert response.status_code == 422
	assert 'exceeds the maximum' in response.json()['detail']


async def test_loan_for_missing_asset_returns_404(api_client) -> None:
	client, session = api_client
	borrower_id = await _seed_user(
		session, 'http-borrower5@example.com', UserRole.staff
	)
	payload = _loan_payload(999_999, borrower_id)
	response = await client.post(
		'/loans', headers={'X-Actor-Id': str(borrower_id)}, json=payload
	)
	assert response.status_code == 404
	assert 'asset 999999 not found' in response.json()['detail']


async def test_staff_cannot_approve_returns_403(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-7')
	requester_id = await _seed_user(
		session, 'http-requester@example.com', UserRole.staff
	)
	create = await client.post(
		'/requests',
		headers={'X-Actor-Id': str(requester_id)},
		json={'asset_id': asset_id, 'justification': 'field work'},
	)
	request_id = create.json()['id']
	staff_id = await _seed_user(
		session, 'http-not-approver@example.com', UserRole.staff
	)
	response = await client.post(
		f'/requests/{request_id}/decision',
		headers={'X-Actor-Id': str(staff_id)},
		json={'decision': 'approved'},
	)
	assert response.status_code == 403
	request = await session.get(Request, request_id)
	assert request.status is RequestStatus.pending


async def test_approval_flow_returns_201_and_writes_audit(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-8')
	requester_id = await _seed_user(
		session, 'http-requester2@example.com', UserRole.staff
	)
	approver_id = await _seed_user(
		session, 'http-approver@example.com', UserRole.approver
	)
	create = await client.post(
		'/requests',
		headers={'X-Actor-Id': str(requester_id)},
		json={'asset_id': asset_id, 'justification': 'client visit'},
	)
	request_id = create.json()['id']
	response = await client.post(
		f'/requests/{request_id}/decision',
		headers={'X-Actor-Id': str(approver_id)},
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
		for event in audit.json()
		if event['action'] == 'request.decide' and event['entity_id'] == request_id
	]
	assert len(events) == 1
	assert events[0]['actor_id'] == approver_id


async def test_decision_on_missing_request_returns_404(api_client) -> None:
	client, session = api_client
	approver_id = await _seed_user(
		session, 'http-approver2@example.com', UserRole.approver
	)
	response = await client.post(
		'/requests/999999/decision',
		headers={'X-Actor-Id': str(approver_id)},
		json={'decision': 'approved'},
	)
	assert response.status_code == 404


async def test_loan_list_renders_asset_and_borrower_names(api_client) -> None:
	client, session = api_client
	category_id = await _seed_category(session)
	asset_id = await _seed_asset(session, category_id, 'HTTP-ASSET-9')
	borrower_id = await _seed_user(
		session, 'http-borrower6@example.com', UserRole.staff
	)
	create = await client.post(
		'/loans',
		headers={'X-Actor-Id': str(borrower_id)},
		json=_loan_payload(asset_id, borrower_id),
	)
	loan_id = create.json()['id']
	# The list joins the asset and borrower names for display — one lazy
	# query per row; the N+1 checkpoint counts those queries next.
	response = await client.get('/loans')
	assert response.status_code == 200
	rows = [row for row in response.json() if row['id'] == loan_id]
	assert len(rows) == 1
	assert rows[0]['asset_name'] == 'MacBook Pro 14'
	assert rows[0]['borrower_name'] == 'http-borrower6'
