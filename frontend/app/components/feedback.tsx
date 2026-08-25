import type { ReactNode } from 'react';

import { Spinner } from './icons';

const ALERT_TONES = {
	green: 'border-green-200 bg-green-50 text-green-800',
	red: 'border-red-200 bg-red-50 text-red-800',
	amber: 'border-amber-200 bg-amber-50 text-amber-800',
	gray: 'border-gray-200 bg-gray-50 text-gray-700',
} as const;

const ALERT_TITLES = {
	green: 'text-green-900',
	red: 'text-red-900',
	amber: 'text-amber-900',
	gray: 'text-gray-900',
} as const;

export function Alert({
	tone = 'red',
	title,
	children,
}: {
	tone?: keyof typeof ALERT_TONES;
	title: string;
	children?: ReactNode;
}) {
	return (
		<div className={`mb-6 rounded-lg border p-4 text-sm ${ALERT_TONES[tone]}`}>
			<p className={`font-medium ${ALERT_TITLES[tone]}`}>{title}</p>
			{children && <div className="mt-1">{children}</div>}
		</div>
	);
}

export function EmptyState({
	title,
	description,
	icon,
}: {
	title: string;
	description?: string;
	icon?: ReactNode;
}) {
	return (
		<div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-gray-300 bg-white px-6 py-12 text-center">
			{icon && <div className="mb-3 h-8 w-8 text-gray-400">{icon}</div>}
			<p className="text-sm font-medium text-gray-900">{title}</p>
			{description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
		</div>
	);
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
	return (
		<div className="flex items-center justify-center gap-2 py-12 text-sm text-gray-500">
			<Spinner className="h-4 w-4" />
			{label}
		</div>
	);
}
