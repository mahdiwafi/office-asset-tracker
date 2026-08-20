'use client';

import { useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
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
	condition_out: string;
	condition_in: string | null;
};

export default function MyLoansPage() {
	const [me, setMe] = useState<Me | null>(null);
	const [loans, setLoans] = useState<Loan[] | null>(null);
	const [error, setError] = useState<string | null>(null);

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

	return (
		<RequireAuth>
			<main className="mx-auto max-w-5xl px-4 py-8">
				<h1 className="mb-4 text-xl font-semibold">My loans</h1>
				{error && <p className="mb-4 text-red-700">{error}</p>}
				{!loans && !error && <p className="text-gray-500">Loading…</p>}
				{loans && loans.length === 0 && <p className="text-gray-500">No loans yet.</p>}
				{loans && loans.length > 0 && (
					<table className="w-full border-collapse bg-white text-sm shadow-sm">
						<thead>
							<tr className="border-b border-gray-200 text-left text-gray-500">
								<th className="px-3 py-2">Asset</th>
								<th className="px-3 py-2">Start</th>
								<th className="px-3 py-2">Due</th>
								<th className="px-3 py-2">Condition out</th>
								<th className="px-3 py-2">Condition in</th>
								<th className="px-3 py-2">Returned</th>
							</tr>
						</thead>
						<tbody>
							{loans.map((loan) => (
								<tr key={loan.id} className="border-b border-gray-100">
									<td className="px-3 py-2">
										<span className="font-medium">{loan.asset_name}</span>{' '}
										<span className="text-gray-500">(#{loan.asset_id})</span>
									</td>
									<td className="px-3 py-2">{loan.start_date.slice(0, 10)}</td>
									<td className="px-3 py-2">{loan.due_date.slice(0, 10)}</td>
									<td className="px-3 py-2">{loan.condition_out}</td>
									<td className="px-3 py-2">{loan.condition_in ?? '—'}</td>
									<td className="px-3 py-2">
										{loan.returned_at ? new Date(loan.returned_at).toLocaleDateString() : '—'}
									</td>
								</tr>
							))}
						</tbody>
					</table>
				)}
			</main>
		</RequireAuth>
	);
}
