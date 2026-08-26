'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { ASSET_STATUS_TONES, CONDITION_TONES, StatusBadge } from '../../components/badge';
import { Button } from '../../components/button';
import { Card } from '../../components/card';
import { Alert, LoadingState } from '../../components/feedback';
import { ArrowLeft, Check, X } from '../../components/icons';
import { PageHeader } from '../../components/page-header';
import { RequireAuth } from '../../components/require-auth';

type Me = {
	id: number;
	role: string;
};

type Asset = {
	id: number;
	inventory_tag: string;
	name: string;
	serial: string | null;
	category_id: number | null;
	status: string;
	condition: string;
};

const APPROVER_ROLES = ['approver', 'admin'];

export default function AssetDetailPage() {
	const { id } = useParams<{ id: string }>();
	const [asset, setAsset] = useState<Asset | null>(null);
	const [me, setMe] = useState<Me | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [acting, setActing] = useState<string | null>(null);

	useEffect(() => {
		api(`/assets/${id}`)
			.then((body) => setAsset(body))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, [id]);

	useEffect(() => {
		// The lifecycle actions are the ICT team's job: sending to
		// maintenance, repairing, and offboarding are approver actions —
		// staff can loan and return.
		api('/users/me')
			.then((body) => setMe(body))
			.catch((e: unknown) => setError(e instanceof ApiError ? e.message : String(e)));
	}, []);

	async function changeStatus(newStatus: string) {
		setActing(newStatus);
		setError(null);
		try {
			// The status endpoint takes the bare enum string as the body.
			const updated = await api(`/assets/${asset?.id}/status`, {
				method: 'PATCH',
				body: newStatus,
			});
			setAsset(updated);
		} catch (e) {
			setError(e instanceof ApiError ? e.message : String(e));
		} finally {
			setActing(null);
		}
	}

	const isApprover = me ? APPROVER_ROLES.includes(me.role) : false;

	return (
		<RequireAuth>
			<main className="mx-auto max-w-3xl px-4 py-8">
				<p className="mb-4">
					<Link
						href="/"
						className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900"
					>
						<ArrowLeft className="h-4 w-4" />
						Asset catalog
					</Link>
				</p>
				<PageHeader title="Asset detail" description={asset?.name} />
				{error && (
					<Alert tone="red" title="Could not update this asset">
						{error}
					</Alert>
				)}
				{!asset && !error && <LoadingState label="Loading asset…" />}
				{asset && (
					<Card className="p-6">
						<div className="flex items-center gap-3">
							<p className="text-lg font-semibold text-gray-900">{asset.name}</p>
							<StatusBadge value={asset.status} tones={ASSET_STATUS_TONES} />
						</div>
						<dl className="mt-6 grid grid-cols-2 gap-x-8 gap-y-5 sm:grid-cols-3">
							<div>
								<dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
									Inventory tag
								</dt>
								<dd className="mt-1 font-mono text-sm text-gray-900">{asset.inventory_tag}</dd>
							</div>
							<div>
								<dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
									Serial number
								</dt>
								<dd className="mt-1 font-mono text-sm text-gray-900">{asset.serial ?? '—'}</dd>
							</div>
							<div>
								<dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
									Category id
								</dt>
								<dd className="mt-1 text-sm text-gray-900">{asset.category_id ?? '—'}</dd>
							</div>
							<div>
								<dt className="text-xs font-medium uppercase tracking-wide text-gray-500">
									Condition
								</dt>
								<dd className="mt-1">
									<StatusBadge value={asset.condition} tones={CONDITION_TONES} />
								</dd>
							</div>
						</dl>
						{isApprover && asset.status !== 'offboarded' && (
							<div className="mt-6 flex flex-wrap gap-2 border-t border-gray-100 pt-5">
								{asset.status !== 'maintenance' && (
									<Button
										variant="secondary"
										busy={acting === 'maintenance'}
										disabled={asset.status === 'loaned'}
										title={
											asset.status === 'loaned'
												? 'Return the loan before sending it to maintenance'
												: 'Flag this asset as in for repair'
										}
										onClick={() => changeStatus('maintenance')}
									>
										Send to maintenance
									</Button>
								)}
								{asset.status === 'maintenance' && (
									<Button
										variant="success"
										busy={acting === 'available'}
										onClick={() => changeStatus('available')}
									>
										<Check className="h-4 w-4" />
										Repair (back to available)
									</Button>
								)}
								{isApprover && (
									<Button
										variant="danger"
										busy={acting === 'offboarded'}
										disabled={asset.status === 'loaned'}
										title={
											asset.status === 'loaned'
												? 'Return the loan before offboarding'
												: 'Retire this asset permanently'
										}
										onClick={() => changeStatus('offboarded')}
									>
										<X className="h-4 w-4" />
										Offboard
									</Button>
								)}
							</div>
						)}
					</Card>
				)}
			</main>
		</RequireAuth>
	);
}
