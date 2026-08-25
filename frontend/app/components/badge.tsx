import type { ReactNode } from 'react';

export type BadgeTone = 'green' | 'blue' | 'amber' | 'red' | 'gray';

const TONE_CLASSES: Record<BadgeTone, string> = {
	green: 'border-green-200 bg-green-50 text-green-700',
	blue: 'border-blue-200 bg-blue-50 text-blue-700',
	amber: 'border-amber-200 bg-amber-50 text-amber-700',
	red: 'border-red-200 bg-red-50 text-red-700',
	gray: 'border-gray-200 bg-gray-100 text-gray-600',
};

// Status pill. The dot is a second cue so colour is never the only signal.
export function Badge({
	tone,
	children,
	dot = true,
}: {
	tone: BadgeTone;
	children: ReactNode;
	dot?: boolean;
}) {
	return (
		<span
			className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${TONE_CLASSES[tone]}`}
		>
			{dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
			{children}
		</span>
	);
}

// Enum → tone maps, mirroring the backend enums (app/models). Unknown
// values fall back to gray rather than crashing the render.
export const ASSET_STATUS_TONES: Record<string, BadgeTone> = {
	available: 'green',
	loaned: 'blue',
	damaged: 'red',
	maintenance: 'amber',
	offboarded: 'gray',
};

export const CONDITION_TONES: Record<string, BadgeTone> = {
	new: 'green',
	good: 'blue',
	fair: 'amber',
	poor: 'red',
};

export const REQUEST_STATUS_TONES: Record<string, BadgeTone> = {
	pending: 'amber',
	approved: 'green',
	declined: 'red',
	cancelled: 'gray',
};

export function StatusBadge({ value, tones }: { value: string; tones: Record<string, BadgeTone> }) {
	return <Badge tone={tones[value] ?? 'gray'}>{value}</Badge>;
}
