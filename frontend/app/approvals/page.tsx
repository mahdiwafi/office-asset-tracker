'use client';

import { useCallback, useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { RequireAuth } from '../components/require-auth';

type Me = {
	id: number;
	role: string;
};

type RequestItem = {
	id: number;
	requester_id: number;
	asset_id: number | null;
	category_id: number | null;
	justification: string;
	status: string;
	created_at: string;
};

const APPROVER_ROLES = ['approver', 'admin'];

export default function ApprovalsPage() {
	const [me, setMe] = useState<Me | null>(null);
	const [pending, setPending] = useState<RequestItem[] | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [actingOn, setActingOn] = useState<number | null>(null);

	const loadQueue = useCallback(() => {
		api('/requests?status=pending')
			.then((body) => setPending(body.items))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	useEffect(() => {
		api('/users/me')
			.then((body) => setMe(body))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	useEffect(() => {
		if (me && APPROVER_ROLES.includes(me.role)) loadQueue();
	}, [me, loadQueue]);

	async function decide(requestId: number, decision: string) {
		setActingOn(requestId);
		setError(null);
		try {
			await api(`/requests/${requestId}/decision`, {
				method: 'POST',
				body: { decision },
			});
			loadQueue();
		} catch (e) {
			setError(e instanceof ApiError ? e.message : String(e));
		} finally {
			setActingOn(null);
		}
	}

	return (
		<RequireAuth>
			<main className="mx-auto max-w-4xl px-4 py-8">
				<h1 className="mb-4 text-xl font-semibold">Approval queue</h1>
				{error && <p className="mb-4 text-red-700">{error}</p>}
				{me && !APPROVER_ROLES.includes(me.role) && (
					<p className="text-gray-600">
						Only approvers can review requests. Your role is <strong>{me.role}</strong> — ask an
						admin to grant you the Approver role in Entra ID if you need to.
					</p>
				)}
				{me && APPROVER_ROLES.includes(me.role) && !pending && !error && (
					<p className="text-gray-500">Loading…</p>
				)}
				{me &&
					APPROVER_ROLES.includes(me.role) &&
					pending &&
					(pending.length === 0 ? (
						<p className="text-gray-500">No pending requests. Nice.</p>
					) : (
						<ul className="space-y-4">
							{pending.map((req) => (
								<li key={req.id} className="rounded border border-gray-200 bg-white p-4">
									<div className="flex items-start justify-between gap-4">
										<div>
											<p className="text-sm font-medium">
												Request #{req.id} · asset #{req.asset_id ?? '—'} · by user{' '}
												{req.requester_id}
											</p>
											<p className="mt-1 text-sm text-gray-700">{req.justification}</p>
											<p className="mt-2 text-xs text-gray-500">
												Created {new Date(req.created_at).toLocaleString()}
											</p>
										</div>
										<div className="flex shrink-0 gap-2">
											<button
												onClick={() => decide(req.id, 'approved')}
												disabled={actingOn === req.id}
												className="rounded bg-green-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-800 disabled:opacity-50"
											>
												Approve
											</button>
											<button
												onClick={() => decide(req.id, 'declined')}
												disabled={actingOn === req.id}
												className="rounded bg-red-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-800 disabled:opacity-50"
											>
												Decline
											</button>
										</div>
									</div>
								</li>
							))}
						</ul>
					))}
			</main>
		</RequireAuth>
	);
}
