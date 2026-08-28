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

type PendingReturn = {
	id: number;
	asset_id: number;
	asset_name: string;
	borrower_id: number;
	borrower_name: string;
	start_date: string;
	due_date: string;
};

type PendingExtend = {
	id: number;
	asset_id: number;
	asset_name: string;
	borrower_id: number;
	borrower_name: string;
	start_date: string;
	due_date: string;
	extend_due_date: string;
};

const APPROVER_ROLES = ['approver', 'admin'];

export default function ApprovalsPage() {
	const [me, setMe] = useState<Me | null>(null);
	const [pending, setPending] = useState<RequestItem[] | null>(null);
	const [returns, setReturns] = useState<PendingReturn[] | null>(null);
	const [extensions, setExtensions] = useState<PendingExtend[] | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [actingOn, setActingOn] = useState<number | null>(null);
	// Per-loan returned condition chosen by the approver at decision time.
	const [returnConditions, setReturnConditions] = useState<Record<number, string>>({});
	const [actingOnReturn, setActingOnReturn] = useState<number | null>(null);
	const [actingOnExtend, setActingOnExtend] = useState<number | null>(null);

	const loadAll = useCallback(() => {
		api('/requests?status=pending')
			.then((body) => setPending(body.items))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
		// Loans whose borrower asked to return them: the return decision
		// lives here, next to the request decisions.
		api('/loans?return_requested=true&limit=50')
			.then((body) => setReturns(body.items))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
		// Loans whose borrower asked for a later due date: extension
		// requests get the same approver decision as returns.
		api('/loans?extend_requested=true&limit=50')
			.then((body) => setExtensions(body.items))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	useEffect(() => {
		api('/users/me')
			.then((body) => setMe(body))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	useEffect(() => {
		if (me && APPROVER_ROLES.includes(me.role)) loadAll();
	}, [me, loadAll]);

	async function decide(requestId: number, decision: string) {
		setActingOn(requestId);
		setError(null);
		try {
			await api(`/requests/${requestId}/decision`, {
				method: 'POST',
				body: { decision },
			});
			loadAll();
		} catch (e) {
			setError(e instanceof ApiError ? e.message : String(e));
		} finally {
			setActingOn(null);
		}
	}

	async function decideExtend(loanId: number, decision: string) {
		setActingOnExtend(loanId);
		setError(null);
		try {
			await api(`/loans/${loanId}/extend/decision`, {
				method: 'POST',
				body: { decision },
			});
			loadAll();
		} catch (e) {
			setError(e instanceof ApiError ? e.message : String(e));
		} finally {
			setActingOnExtend(null);
		}
	}

	async function decideReturn(loanId: number, decision: string) {
		setActingOnReturn(loanId);
		setError(null);
		try {
			await api(`/loans/${loanId}/return/decision`, {
				method: 'POST',
				body: {
					decision,
					// The approver grades the return; the condition only
					// matters when the return is accepted.
					...(decision === 'approved'
						? { condition_in: returnConditions[loanId] ?? 'good' }
						: {}),
				},
			});
			loadAll();
		} catch (e) {
			setError(e instanceof ApiError ? e.message : String(e));
		} finally {
			setActingOnReturn(null);
		}
	}

	return (
		<RequireAuth>
			<main className="mx-auto max-w-4xl px-4 py-8">
				<PageHeader
					title="Approval queue"
					description="Pending requests, returns, and extensions waiting for a decision."
				/>
				{error && (
					<Alert tone="red" title="Something went wrong">
						{error}
					</Alert>
				)}
				{me && !APPROVER_ROLES.includes(me.role) && (
					<Alert tone="amber" title="Approver role required">
						<p className="text-amber-800">
							Only approvers can review requests, returns, and extensions. Your role is{' '}
							<strong>{me.role}</strong> — ask an admin to grant you the Approver role in
							Entra ID if you need to.
						</p>
					</Alert>
				)}
				{me &&
					APPROVER_ROLES.includes(me.role) &&
					!pending &&
					!returns &&
					!extensions &&
					!error && <LoadingState label="Loading decisions…" />}
				{me &&
					APPROVER_ROLES.includes(me.role) &&
					pending &&
					returns &&
					extensions &&
					(pending.length === 0 && returns.length === 0 && extensions.length === 0 ? (
						<EmptyState
							title="Nothing to review"
							description="New requests, returns, and extensions will appear here."
							icon={<Check className="h-8 w-8" />}
						/>
					) : (
						<div className="space-y-8">
							{pending.length > 0 && (
								<section>
									<h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-gray-500">
										Requests · {pending.length}
									</h2>
									<ul className="space-y-4">
										{pending.map((req) => (
											<li key={req.id}>
												<Card className="p-4 transition-colors hover:border-gray-300">
													<div className="flex items-start justify-between gap-4">
														<div>
															<div className="flex items-center gap-2">
																<p className="text-sm font-medium text-gray-900">
																	Request #{req.id}
																</p>
																<StatusBadge
																	value={req.status}
																	tones={REQUEST_STATUS_TONES}
																/>
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
								</section>
							)}
							{returns.length > 0 && (
								<section>
									<h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-gray-500">
										Pending returns · {returns.length}
									</h2>
									<Card className="overflow-hidden">
										<table className="w-full text-sm">
											<thead>
												<tr className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
													<th className="px-4 py-3 font-medium">Asset</th>
													<th className="px-4 py-3 font-medium">Borrower</th>
													<th className="px-4 py-3 font-medium">Due</th>
													<th className="px-4 py-3 font-medium">Condition in</th>
													<th className="px-4 py-3 font-medium">Actions</th>
												</tr>
											</thead>
											<tbody>
												{returns.map((loan) => (
													<tr key={loan.id} className="border-t border-gray-100">
														<td className="px-4 py-3">
															<span className="font-medium text-gray-900">{loan.asset_name}</span>{' '}
															<span className="text-gray-500">(#{loan.asset_id})</span>
														</td>
														<td className="px-4 py-3">{loan.borrower_name}</td>
														<td className="px-4 py-3">{loan.due_date.slice(0, 10)}</td>
														<td className="px-4 py-3">
															<select
																value={returnConditions[loan.id] ?? 'good'}
																onChange={(e) =>
																	setReturnConditions((prev) => ({
																		...prev,
																		[loan.id]: e.target.value,
																	}))
																}
																className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
																aria-label="Returned condition"
															>
																<option value="good">Good</option>
																<option value="fair">Fair</option>
																<option value="poor">Poor</option>
															</select>
														</td>
														<td className="px-4 py-3">
															<div className="flex gap-2">
																<Button
																	variant="success"
																	busy={actingOnReturn === loan.id}
																	onClick={() => decideReturn(loan.id, 'approved')}
																>
																	<Check className="h-4 w-4" />
																	Accept return
																</Button>
																<Button
																	variant="danger"
																	disabled={actingOnReturn === loan.id}
																	onClick={() => decideReturn(loan.id, 'declined')}
																>
																	<X className="h-4 w-4" />
																	Decline
																</Button>
															</div>
														</td>
													</tr>
												))}
											</tbody>
										</table>
									</Card>
								</section>
							)}
							{extensions.length > 0 && (
								<section>
									<h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-gray-500">
										Pending extensions · {extensions.length}
									</h2>
									<Card className="overflow-hidden">
										<table className="w-full text-sm">
											<thead>
												<tr className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
													<th className="px-4 py-3 font-medium">Asset</th>
													<th className="px-4 py-3 font-medium">Borrower</th>
													<th className="px-4 py-3 font-medium">Due</th>
													<th className="px-4 py-3 font-medium">New due</th>
													<th className="px-4 py-3 font-medium">Actions</th>
												</tr>
											</thead>
											<tbody>
												{extensions.map((loan) => (
													<tr key={loan.id} className="border-t border-gray-100">
														<td className="px-4 py-3">
															<span className="font-medium text-gray-900">{loan.asset_name}</span>{' '}
															<span className="text-gray-500">(#{loan.asset_id})</span>
														</td>
														<td className="px-4 py-3">{loan.borrower_name}</td>
														<td className="px-4 py-3">{loan.due_date.slice(0, 10)}</td>
														<td className="px-4 py-3">
{loan.extend_due_date.slice(0, 10)}
														</td>
														<td className="px-4 py-3">
															<div className="flex gap-2">
																<Button
																	variant="success"
																	busy={actingOnExtend === loan.id}
																	onClick={() => decideExtend(loan.id, 'approved')}
																>
																	<Check className="h-4 w-4" />
																	Approve
																</Button>
																<Button
																	variant="danger"
																	disabled={actingOnExtend === loan.id}
																	onClick={() => decideExtend(loan.id, 'declined')}
																>
																	<X className="h-4 w-4" />
																	Decline
																</Button>
															</div>
														</td>
													</tr>
												))}
											</tbody>
										</table>
									</Card>
								</section>
							)}
						</div>
					))}
			</main>
		</RequireAuth>
	);
}
