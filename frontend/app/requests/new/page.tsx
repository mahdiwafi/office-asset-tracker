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
	loaned_until: string | null;
};

type RaisedRequest = {
	id: number;
	status: string;
	created_at: string;
};

function isoDaysFromNow(days: number): string {
	const date = new Date();
	date.setDate(date.getDate() + days);
	return date.toLocaleDateString('en-CA');
}

const INPUT_CLASSES =
	'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600/20';

export default function RaiseRequestPage() {
	const [assets, setAssets] = useState<Asset[] | null>(null);
	const [assetId, setAssetId] = useState('');
	const [justification, setJustification] = useState('');
	// Pre-filled with the standard two-week window so an approval always
	// has a period to issue the loan from; both are editable, and clearing
	// one clears the rule (see handleSubmit).
	const [startDate, setStartDate] = useState(() => isoDaysFromNow(0));
	const [dueDate, setDueDate] = useState(() => isoDaysFromNow(14));
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
		// Dates go together: a request with only one end of the period is a
		// mistake, and approval issues the loan from the pair. ISO date
		// strings compare lexicographically, so no date library is needed.
		if ((startDate && !dueDate) || (!startDate && dueDate)) {
			setError('Start and due dates go together — pick both or leave both empty.');
			return;
		}
		if (startDate && dueDate) {
			if (dueDate <= startDate) {
				setError('The due date must be after the start date.');
				return;
			}
			if ((Date.parse(dueDate) - Date.parse(startDate)) / 86400000 > 30) {
				setError('Loan periods are capped at 30 days.');
				return;
			}
		}
		setSubmitting(true);
		setError(null);
		try {
			const body = await api('/requests', {
				method: 'POST',
				body: {
					asset_id: Number(assetId),
					justification,
					// Both or neither (enforced above); an empty pair stays a
					// consent-only request.
					...(startDate && dueDate
						? { start_date: startDate, due_date: dueDate }
						: {}),
				},
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
											{asset.inventory_tag} — {asset.name} (
											{asset.status}
											{asset.loaned_until
												? ` until ${asset.loaned_until.slice(0, 10)}`
												: ''}
											)
										</option>
									))}
								</select>
								{(() => {
									const selected = assets.find(
										(a) => a.id === Number(assetId)
									);
									return selected?.loaned_until ? (
										<p className="mt-1 text-xs text-amber-700">
											This asset is on loan until{' '}
											{selected.loaned_until.slice(0, 10)} — pick a
											window after that date.
										</p>
									) : null;
								})()}
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
							<div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
								<div>
									<label
										htmlFor="start-date"
										className="mb-1 block text-sm font-medium text-gray-700"
									>
										Start date
									</label>
									<input
										id="start-date"
										type="date"
										value={startDate}
										min={isoDaysFromNow(0)}
										onChange={(e) => setStartDate(e.target.value)}
										className={INPUT_CLASSES}
									/>
								</div>
								<div>
									<label
										htmlFor="due-date"
										className="mb-1 block text-sm font-medium text-gray-700"
									>
										Due date
									</label>
									<input
										id="due-date"
										type="date"
										value={dueDate}
										min={startDate}
										onChange={(e) => setDueDate(e.target.value)}
										className={INPUT_CLASSES}
									/>
								</div>
							</div>
							<p className="text-xs text-gray-500">
								Optional — but an approval issues the loan for exactly this period
								(capped at 30 days), so fill both when you know the dates.
							</p>
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
