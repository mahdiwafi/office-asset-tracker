'use client';

import { useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { RequireAuth } from '../components/require-auth';

type Entry = {
	id: number;
	actor_id: number | null;
	action: string;
	entity_type: string;
	entity_id: number;
	before: Record<string, unknown> | null;
	after: Record<string, unknown> | null;
	at: string;
};

export default function AuditPage() {
	const [entries, setEntries] = useState<Entry[] | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		api('/audit')
			.then((body) => setEntries(body.items))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	return (
		<RequireAuth>
			<main className="mx-auto max-w-6xl px-4 py-8">
				<h1 className="mb-4 text-xl font-semibold">Audit log</h1>
				{error && <p className="mb-4 text-red-700">{error}</p>}
				{!entries && !error && <p className="text-gray-500">Loading…</p>}
				{entries && entries.length === 0 && <p className="text-gray-500">No entries yet.</p>}
				{entries && entries.length > 0 && (
					<div className="overflow-x-auto">
						<table className="w-full border-collapse bg-white text-sm shadow-sm">
							<thead>
								<tr className="border-b border-gray-200 text-left text-gray-500">
									<th className="px-3 py-2">When</th>
									<th className="px-3 py-2">Actor</th>
									<th className="px-3 py-2">Action</th>
									<th className="px-3 py-2">Entity</th>
									<th className="px-3 py-2">Before → After</th>
								</tr>
							</thead>
							<tbody>
								{entries.map((entry) => (
									<tr key={entry.id} className="border-b border-gray-100 align-top">
										<td className="whitespace-nowrap px-3 py-2">
											{new Date(entry.at).toLocaleString()}
										</td>
										<td className="px-3 py-2 font-mono">{entry.actor_id ?? 'system'}</td>
										<td className="px-3 py-2">{entry.action}</td>
										<td className="px-3 py-2 font-mono">
											{entry.entity_type}#{entry.entity_id}
										</td>
										<td className="px-3 py-2">
											<pre className="whitespace-pre-wrap font-mono text-xs text-gray-600">
												{JSON.stringify(entry.before)}
												{' → '}
												{JSON.stringify(entry.after)}
											</pre>
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				)}
			</main>
		</RequireAuth>
	);
}
