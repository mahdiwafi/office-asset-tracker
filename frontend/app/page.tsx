'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { RequireAuth } from './components/require-auth';

type Asset = {
	id: number;
	inventory_tag: string;
	name: string;
	serial: string | null;
	status: string;
	condition: string;
};

export default function AssetListPage() {
	const [assets, setAssets] = useState<Asset[] | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		api('/assets')
			.then((body) => setAssets(body.items))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	return (
		<RequireAuth>
			<main className="mx-auto max-w-5xl px-4 py-8">
				<h1 className="mb-4 text-xl font-semibold">Asset catalog</h1>
				{error && <p className="mb-4 text-red-700">{error}</p>}
				{!assets && !error && <p className="text-gray-500">Loading…</p>}
				{assets && (
					<table className="w-full border-collapse bg-white text-sm shadow-sm">
						<thead>
							<tr className="border-b border-gray-200 text-left text-gray-500">
								<th className="px-3 py-2">Tag</th>
								<th className="px-3 py-2">Name</th>
								<th className="px-3 py-2">Status</th>
								<th className="px-3 py-2">Condition</th>
							</tr>
						</thead>
						<tbody>
							{assets.map((asset) => (
								<tr key={asset.id} className="border-b border-gray-100">
									<td className="px-3 py-2 font-mono">{asset.inventory_tag}</td>
									<td className="px-3 py-2">
										<Link href={`/assets/${asset.id}`} className="text-blue-700 hover:underline">
											{asset.name}
										</Link>
									</td>
									<td className="px-3 py-2">{asset.status}</td>
									<td className="px-3 py-2">{asset.condition}</td>
								</tr>
							))}
						</tbody>
					</table>
				)}
				{assets && assets.length === 0 && <p className="text-gray-500">No assets yet.</p>}
			</main>
		</RequireAuth>
	);
}
