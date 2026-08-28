'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { Badge, CONDITION_TONES, StatusBadge } from '../components/badge';
import { Button } from '../components/button';
import { Card, StatCard } from '../components/card';
import { Alert, EmptyState, LoadingState } from '../components/feedback';
import { Calendar, Check, Info } from '../components/icons';
import { PageHeader } from '../components/page-header';
import { RequireAuth } from '../components/require-auth';

type Me = {
	id: number;
};

type Loan = {
	id: number;
	asset_id: number;
	asset_name: string;
	borrower_id: number;
	borrower_name: string;
	start_date: string;
	due_date: string;
	returned_at: string | null;
	return_requested_at: string | null;
	extend_requested_at: string | null;
	extend_due_date: string | null;
	condition_out: string;
	condition_in: string | null;
};

// Both dates are YYYY-MM-DD, so a plain string comparison is a date
// comparison — no date library, no timezone parsing.
const isOverdue = (loan: Loan) =>
	!loan.returned_at && loan.due_date < new Date().toLocaleDateString('en-CA');

// A sensible default for the extension picker: a week past the current
// due date, computed in UTC so the date math never crosses a timezone.
const weekLater = (date: string) => {
	const [y, m, d] = date.split('-').map(Number);
	return new Date(Date.UTC(y, m - 1, d + 7)).toISOString().slice(0, 10);
};

export default function MyLoansPage() {
	const [me, setMe] = useState<Me | null>(null);
	const [loans, setLoans] = useState<Loan[] | null>(null);
	const [error, setError] = useState<string | null>(null);
	// The row whose return request POST is in flight.
	const [requestingId, setRequestingId] = useState<number | null>(null);
	// The row whose extension form is open, its chosen date, and the POST
	// in flight — extension is a request too (an approver decides), so the
	// due date never moves from this page.
	const [extendingId, setExtendingId] = useState<number | null>(null);
	const [extendDues, setExtendDues] = useState<Record<number, string>>({});
	const [extendingBusy, setExtendingBusy] = useState<number | null>(null);

	useEffect(() => {
		api('/users/me')
			.then((body) => setMe(body))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	useEffect(() => {
		if (!me) return;
		api(`/loans?borrower_id=${me.id}`)
			.then((body) => setLoans(body.items))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, [me]);

	async function handleRequestExtend(loanId: number) {
		const newDue = extendDues[loanId];
		if (!newDue) return;
		setExtendingBusy(loanId);
		setError(null);
		try {
			await api(`/loans/${loanId}/extend`, {
				method: 'POST',
				body: { new_due_date: newDue },
			});
			if (!me) return;
			const body = await api(`/loans?borrower_id=${me.id}`);
			setLoans(body.items);
			setExtendingId(null);
		} catch (e) {
			setError(e instanceof ApiError ? e.message : String(e));
		} finally {
			setExtendingBusy(null);
		}
	}

	async function handleRequestReturn(loanId: number) {
		setRequestingId(loanId);
		setError(null);
		try {
			// The borrower only asks to return — no condition. An approver
			// grades the return and closes the loan on the approvals page.
			await api(`/loans/${loanId}/return`, { method: 'POST' });
			if (!me) return;
			const body = await api(`/loans?borrower_id=${me.id}`);
			setLoans(body.items);
		} catch (e) {
			setError(e instanceof ApiError ? e.message : String(e));
		} finally {
			setRequestingId(null);
		}
	}

	const counts = {
		active: loans?.filter((l) => !l.returned_at && !isOverdue(l)).length ?? 0,
		overdue: loans?.filter(isOverdue).length ?? 0,
		returned: loans?.filter((l) => l.returned_at).length ?? 0,
	};

	return (
		<RequireAuth>
			<main className="mx-auto w-full max-w-6xl px-4 py-8">
				<PageHeader title="My loans" description="Loans issued to you, with due dates." />
				{error && (
					<Alert tone="red" title="Something went wrong">
						{error}
					</Alert>
				)}
				{!loans && !error && <LoadingState label="Loading loans…" />}
				{loans && (
					<>
						<div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
							<StatCard
								label="Active"
								value={counts.active}
								icon={<Calendar className="h-4 w-4" />}
							/>
							<StatCard
								label="Overdue"
								value={counts.overdue}
								tone="red"
								icon={<Info className="h-4 w-4" />}
							/>
							<StatCard
								label="Returned"
								value={counts.returned}
								tone="gray"
								icon={<Check className="h-4 w-4" />}
							/>
						</div>
						{loans.length === 0 ? (
							<EmptyState
								title="No loans yet"
								description="Loans appear here once your requests are approved."
								icon={<Calendar className="h-8 w-8" />}
							/>
						) : (
							<Card className="overflow-hidden">
								<table className="w-full text-sm">
									<thead>
										<tr className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
											<th className="px-4 py-3 font-medium">Asset</th>
											<th className="px-4 py-3 font-medium">Start</th>
											<th className="px-4 py-3 font-medium">Due</th>
											<th className="px-4 py-3 font-medium">Condition out</th>
											<th className="px-4 py-3 font-medium">Condition in</th>
											<th className="px-4 py-3 font-medium">Status</th>
											<th className="px-4 py-3 font-medium">Actions</th>
										</tr>
									</thead>
									<tbody>
										{loans.map((loan) => {
											const overdue = isOverdue(loan);
											return (
												<tr
													key={loan.id}
													className={`border-t border-gray-100 transition-colors hover:bg-gray-50 ${
														overdue ? 'bg-red-50/50' : ''
													}`}
												>
													<td className="px-4 py-3">
														<Link
															href={`/assets/${loan.asset_id}`}
															className="font-medium text-blue-700 hover:underline"
														>
															{loan.asset_name}
														</Link>{' '}
														<span className="text-gray-500">(#{loan.asset_id})</span>
													</td>
													<td className="px-4 py-3">{loan.start_date.slice(0, 10)}</td>
													<td
														className={`px-4 py-3 ${
															overdue ? 'font-medium text-red-700' : ''
														}`}
													>
														{loan.due_date.slice(0, 10)}
													</td>
													<td className="px-4 py-3">
														<StatusBadge value={loan.condition_out} tones={CONDITION_TONES} />
													</td>
													<td className="px-4 py-3">
														{loan.condition_in ? (
															<StatusBadge value={loan.condition_in} tones={CONDITION_TONES} />
														) : (
															<span className="text-gray-400">—</span>
														)}
													</td>
													<td className="px-4 py-3">
														{loan.returned_at ? (
															<Badge tone="gray">Returned</Badge>
														) : overdue ? (
															<Badge tone="red">Overdue</Badge>
														) : (
															<Badge tone="blue">Active</Badge>
														)}
													</td>
													<td className="px-4 py-3">
														{loan.returned_at ? (
															<span className="text-gray-300">—</span>
														) : loan.return_requested_at ? (
															<Badge tone="amber">Return requested</Badge>
														) : loan.extend_requested_at ? (
															<Badge tone="amber">Extension pending</Badge>
														) : extendingId === loan.id ? (
															<div className="flex items-center gap-2">
																<input
																	type="date"
																	value={extendDues[loan.id] ?? weekLater(loan.due_date)}
																	min={loan.due_date.slice(0, 10)}
																	onChange={(e) =>
																		setExtendDues((prev) => ({
																			...prev,
																			[loan.id]: e.target.value,
																		}))
																	}
																	className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
																	aria-label="New due date"
																/>
																<Button
																	variant="secondary"
																	busy={extendingBusy === loan.id}
																	onClick={() => handleRequestExtend(loan.id)}
																>
																	Send
																</Button>
																<button
																	onClick={() => setExtendingId(null)}
																	className="text-sm text-gray-500 hover:text-gray-700"
																>
																	Cancel
																</button>
															</div>
														) : (
															<div className="flex gap-2">
																<Button
																	variant="secondary"
																	onClick={() => setExtendingId(loan.id)}
																>
																	Extend
																</Button>
																<Button
																	variant="secondary"
																	busy={requestingId === loan.id}
																	onClick={() => handleRequestReturn(loan.id)}
																>
																	Request return
																</Button>
															</div>
														)}
													</td>
												</tr>
											);
										})}
									</tbody>
								</table>
							</Card>
						)}
					</>
				)}
			</main>
		</RequireAuth>
	);
}
