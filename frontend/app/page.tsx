'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { ASSET_STATUS_TONES, CONDITION_TONES, StatusBadge } from './components/badge';
import { Card, StatCard } from './components/card';
import { Alert, EmptyState, LoadingState } from './components/feedback';
import { Box, Calendar, Check, Info } from './components/icons';
import { PageHeader } from './components/page-header';
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

	const counts = {
		total: assets?.length ?? 0,
		available: assets?.filter((a) => a.status === 'available').length ?? 0,
		loaned: assets?.filter((a) => a.status === 'loaned').length ?? 0,
		damaged: assets?.filter((a) => a.status === 'damaged').length ?? 0,
	};

	return (
		<RequireAuth>
			<main className="mx-auto w-full max-w-6xl px-4 py-8">
				<PageHeader title="Asset catalog" description="All ICT equipment and its current state." />
				{error && (
					<Alert tone="red" title="Could not load assets">
						{error}
					</Alert>
				)}
				{!assets && !error && <LoadingState label="Loading assets…" />}
				{assets && (
					<>
						<div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
							<StatCard label="Total assets" value={counts.total} icon={<Box className="h-4 w-4" />} />
							<StatCard
								label="Available"
								value={counts.available}
								tone="green"
								icon={<Check className="h-4 w-4" />}
							/>
							<StatCard
								label="On loan"
								value={counts.loaned}
								icon={<Calendar className="h-4 w-4" />}
							/>
							<StatCard
								label="Damaged"
								value={counts.damaged}
								tone="red"
								icon={<Info className="h-4 w-4" />}
							/>
						</div>
						{assets.length === 0 ? (
							<EmptyState
								title="No assets yet"
								description="Assets appear here once they are added to the system."
								icon={<Box className="h-8 w-8" />}
							/>
						) : (
							<Card className="overflow-hidden">
								<table className="w-full text-sm">
									<thead>
										<tr className="bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
											<th className="px-4 py-3 font-medium">Tag</th>
											<th className="px-4 py-3 font-medium">Name</th>
											<th className="px-4 py-3 font-medium">Status</th>
											<th className="px-4 py-3 font-medium">Condition</th>
										</tr>
									</thead>
									<tbody>
										{assets.map((asset) => (
											<tr
												key={asset.id}
												className="border-t border-gray-100 transition-colors hover:bg-gray-50"
											>
												<td className="px-4 py-3 font-mono text-xs">{asset.inventory_tag}</td>
												<td className="px-4 py-3">
													<Link
														href={`/assets/${asset.id}`}
														className="font-medium text-blue-700 hover:underline"
													>
														{asset.name}
													</Link>
												</td>
												<td className="px-4 py-3">
													<StatusBadge value={asset.status} tones={ASSET_STATUS_TONES} />
												</td>
												<td className="px-4 py-3">
													<StatusBadge value={asset.condition} tones={CONDITION_TONES} />
												</td>
											</tr>
										))}
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
