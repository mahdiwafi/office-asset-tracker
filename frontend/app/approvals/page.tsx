'use client';

import { useCallback, useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { REQUEST_STATUS_TONES, StatusBadge } from '../components/badge';
import { Button } from '../components/button';
import { Card } from '../components/card';
import { Alert, EmptyState, LoadingState } from '../components/feedback';
import { Check, X } from '../components/icons';
import { PageHeader } from '../components/page-header';
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
				<PageHeader
					title="Approval queue"
					description="Pending requests waiting for a decision."
				/>
				{error && (
					<Alert tone="red" title="Something went wrong">
						{error}
					</Alert>
				)}
				{me && !APPROVER_ROLES.includes(me.role) && (
					<Alert tone="amber" title="Approver role required">
						<p className="text-amber-800">
							Only approvers can review requests. Your role is <strong>{me.role}</strong> — ask an
							admin to grant you the Approver role in Entra ID if you need to.
						</p>
					</Alert>
				)}
				{me && APPROVER_ROLES.includes(me.role) && !pending && !error && (
					<LoadingState label="Loading requests…" />
				)}
				{me &&
					APPROVER_ROLES.includes(me.role) &&
					pending &&
					(pending.length === 0 ? (
						<EmptyState
							title="No pending requests"
							description="New requests will appear here for review."
							icon={<Check className="h-8 w-8" />}
						/>
					) : (
						<ul className="space-y-4">
							{pending.map((req) => (
								<li key={req.id}>
									<Card className="p-4 transition-colors hover:border-gray-300">
										<div className="flex items-start justify-between gap-4">
											<div>
												<div className="flex items-center gap-2">
													<p className="text-sm font-medium text-gray-900">Request #{req.id}</p>
													<StatusBadge value={req.status} tones={REQUEST_STATUS_TONES} />
												</div>
												<p className="mt-1 font-mono text-xs text-gray-500">
													asset #{req.asset_id ?? '—'} · by user {req.requester_id}
												</p>
												<p className="mt-2 text-sm text-gray-600">{req.justification}</p>
												<p className="mt-2 text-xs text-gray-400">
													Created {new Date(req.created_at).toLocaleString()}
												</p>
											</div>
											<div className="flex shrink-0 gap-2">
												<Button
													variant="success"
													busy={actingOn === req.id}
													onClick={() => decide(req.id, 'approved')}
												>
													<Check className="h-4 w-4" />
													Approve
												</Button>
												<Button
													variant="danger"
													disabled={actingOn === req.id}
													onClick={() => decide(req.id, 'declined')}
												>
													<X className="h-4 w-4" />
													Decline
												</Button>
											</div>
										</div>
									</Card>
								</li>
							))}
						</ul>
					))}
			</main>
		</RequireAuth>
	);
}
