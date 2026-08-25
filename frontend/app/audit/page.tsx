'use client';

import { useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { Card } from '../components/card';
import { Alert, EmptyState, LoadingState } from '../components/feedback';
import { PageHeader } from '../components/page-header';
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

function JsonBlock({ value, label }: { value: Record<string, unknown> | null; label: string }) {
	return (
		<div>
			<p className="text-xs font-medium text-gray-500">{label}</p>
			<pre className="mt-1 whitespace-pre-wrap rounded-md bg-gray-50 p-3 font-mono text-xs text-gray-600">
				{value ? JSON.stringify(value, null, 2) : '—'}
			</pre>
		</div>
	);
}

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
			<main className="mx-auto w-full max-w-6xl px-4 py-8">
				<PageHeader
					title="Audit log"
					description="Append-only record of every change, in the order it happened."
				/>
				{error && (
					<Alert tone="red" title="Could not load the audit log">
						{error}
					</Alert>
				)}
				{!entries && !error && <LoadingState label="Loading audit entries…" />}
				{entries && entries.length === 0 && (
					<EmptyState
						title="No entries yet"
						description="Every change will be recorded here."
					/>
				)}
				{entries && entries.length > 0 && (
					<Card className="overflow-hidden">
						<div className="overflow-x-auto">
							<table className="w-full text-sm">
								<thead>
									<tr className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
										<th className="px-4 py-3 font-medium">When</th>
										<th className="px-4 py-3 font-medium">Actor</th>
										<th className="px-4 py-3 font-medium">Action</th>
										<th className="px-4 py-3 font-medium">Entity</th>
										<th className="px-4 py-3 font-medium">Changes</th>
									</tr>
								</thead>
								<tbody>
									{entries.map((entry) => (
										<tr
											key={entry.id}
											className="border-t border-gray-100 align-top transition-colors hover:bg-gray-50"
										>
											<td className="whitespace-nowrap px-4 py-3">
												{new Date(entry.at).toLocaleString()}
											</td>
											<td className="px-4 py-3">
												{entry.actor_id ? (
													<span className="font-mono">{entry.actor_id}</span>
												) : (
													<span className="font-mono italic text-gray-400">system</span>
												)}
											</td>
											<td className="px-4 py-3">
												<span className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs text-gray-600">
													{entry.action}
												</span>
											</td>
											<td className="px-4 py-3 font-mono">
												{entry.entity_type}#{entry.entity_id}
											</td>
											<td className="px-4 py-3">
												<details>
													<summary className="cursor-pointer list-none text-xs font-medium text-blue-700 hover:underline [&::-webkit-details-marker]:hidden">
														View changes
													</summary>
													<div className="mt-3 grid grid-cols-1 gap-4 lg:grid-cols-2">
														<JsonBlock value={entry.before} label="Before" />
														<JsonBlock value={entry.after} label="After" />
													</div>
												</details>
											</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					</Card>
				)}
			</main>
		</RequireAuth>
	);
}
