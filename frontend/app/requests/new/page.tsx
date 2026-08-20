'use client';

import { FormEvent, useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { RequireAuth } from '../../components/require-auth';

type Asset = {
	id: number;
	inventory_tag: string;
	name: string;
	status: string;
};

type RaisedRequest = {
	id: number;
	status: string;
	created_at: string;
};

export default function RaiseRequestPage() {
	const [assets, setAssets] = useState<Asset[] | null>(null);
	const [assetId, setAssetId] = useState('');
	const [justification, setJustification] = useState('');
	const [submitting, setSubmitting] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [created, setCreated] = useState<RaisedRequest | null>(null);

	useEffect(() => {
		api('/assets')
			.then((body) => {
				setAssets(body.items);
				if (body.items.length > 0) setAssetId(String(body.items[0].id));
			})
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	async function handleSubmit(e: FormEvent) {
		e.preventDefault();
		setSubmitting(true);
		setError(null);
		try {
			const body = await api('/requests', {
				method: 'POST',
				body: { asset_id: Number(assetId), justification },
			});
			setCreated(body);
			setJustification('');
		} catch (err) {
			setError(err instanceof ApiError ? err.message : String(err));
		} finally {
			setSubmitting(false);
		}
	}

	return (
		<RequireAuth>
			<main className="mx-auto max-w-2xl px-4 py-8">
				<h1 className="mb-4 text-xl font-semibold">Raise a request</h1>
				{error && <p className="mb-4 text-red-700">{error}</p>}
				{created && (
					<div className="mb-6 rounded border border-green-200 bg-green-50 p-4 text-sm">
						<p className="font-medium text-green-900">
							Request #{created.id} submitted ({created.status}).
						</p>
						<p className="mt-1 text-green-800">
							An approver will review it. Track it on the Approvals page (approvers) — you can
							also raise another request below.
						</p>
					</div>
				)}
				{!assets && !error && <p className="text-gray-500">Loading assets…</p>}
				{assets && (
					<form
						onSubmit={handleSubmit}
						className="space-y-4 rounded border border-gray-200 bg-white p-6"
					>
						<div>
							<label htmlFor="asset" className="mb-1 block text-sm font-medium text-gray-700">
								Asset
							</label>
							<select
								id="asset"
								value={assetId}
								onChange={(e) => setAssetId(e.target.value)}
								className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
							>
								{assets.map((asset) => (
									<option key={asset.id} value={asset.id}>
										{asset.inventory_tag} — {asset.name} ({asset.status})
									</option>
								))}
							</select>
						</div>
						<div>
							<label
								htmlFor="justification"
								className="mb-1 block text-sm font-medium text-gray-700"
							>
								Justification
							</label>
							<textarea
								id="justification"
								value={justification}
								onChange={(e) => setJustification(e.target.value)}
								required
								rows={4}
								placeholder="Why do you need this equipment?"
								className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
							/>
						</div>
						<button
							type="submit"
							disabled={submitting}
							className="rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
						>
							{submitting ? 'Submitting…' : 'Submit request'}
						</button>
					</form>
				)}
			</main>
		</RequireAuth>
	);
}
