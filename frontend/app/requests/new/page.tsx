'use client';

import { FormEvent, useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { Button } from '../../components/button';
import { Card } from '../../components/card';
import { Alert, LoadingState } from '../../components/feedback';
import { Plus } from '../../components/icons';
import { PageHeader } from '../../components/page-header';
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

const INPUT_CLASSES =
	'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600/20';

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
				<PageHeader
					title="Raise a request"
					description="Ask for equipment — an approver will review it."
				/>
				{error && (
					<Alert tone="red" title="Could not submit the request">
						{error}
					</Alert>
				)}
				{created && (
					<Alert tone="green" title={`Request #${created.id} submitted (${created.status}).`}>
						<p className="text-green-800">
							An approver will review it. Track it on the Approvals page (approvers) — you can
							also raise another request below.
						</p>
					</Alert>
				)}
				{!assets && !error && <LoadingState label="Loading assets…" />}
				{assets && (
					<Card className="p-6">
						<form onSubmit={handleSubmit} className="space-y-4">
							<div>
								<label htmlFor="asset" className="mb-1 block text-sm font-medium text-gray-700">
									Asset
								</label>
								<select
									id="asset"
									value={assetId}
									onChange={(e) => setAssetId(e.target.value)}
									className={INPUT_CLASSES}
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
									className={INPUT_CLASSES}
								/>
							</div>
							<Button type="submit" busy={submitting}>
								<Plus className="h-4 w-4" />
								Submit request
							</Button>
						</form>
					</Card>
				)}
			</main>
		</RequireAuth>
	);
}
