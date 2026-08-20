'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { RequireAuth } from '../../components/require-auth';

type Asset = {
	id: number;
	inventory_tag: string;
	name: string;
	serial: string | null;
	category_id: number | null;
	status: string;
	condition: string;
};

export default function AssetDetailPage() {
	const { id } = useParams<{ id: string }>();
	const [asset, setAsset] = useState<Asset | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		api(`/assets/${id}`)
			.then((body) => setAsset(body))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, [id]);

	return (
		<RequireAuth>
			<main className="mx-auto max-w-3xl px-4 py-8">
				<p className="mb-4">
					<Link href="/" className="text-sm text-blue-700 hover:underline">
						← Asset catalog
					</Link>
				</p>
				<h1 className="mb-4 text-xl font-semibold">Asset detail</h1>
				{error && <p className="mb-4 text-red-700">{error}</p>}
				{!asset && !error && <p className="text-gray-500">Loading…</p>}
				{asset && (
					<dl className="grid grid-cols-2 gap-4 rounded border border-gray-200 bg-white p-6 text-sm">
						<dt className="text-gray-500">Inventory tag</dt>
						<dd className="font-mono">{asset.inventory_tag}</dd>
						<dt className="text-gray-500">Name</dt>
						<dd>{asset.name}</dd>
						<dt className="text-gray-500">Serial number</dt>
						<dd className="font-mono">{asset.serial ?? '—'}</dd>
						<dt className="text-gray-500">Category id</dt>
						<dd>{asset.category_id ?? '—'}</dd>
						<dt className="text-gray-500">Status</dt>
						<dd>{asset.status}</dd>
						<dt className="text-gray-500">Condition</dt>
						<dd>{asset.condition}</dd>
					</dl>
				)}
			</main>
		</RequireAuth>
	);
}
