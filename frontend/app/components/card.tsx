import type { ReactNode } from 'react';

import type { BadgeTone } from './badge';

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
	return (
		<div className={`rounded-lg border border-gray-200 bg-white shadow-sm ${className}`}>
			{children}
		</div>
	);
}

const CHIP_TONES: Record<BadgeTone, string> = {
	green: 'bg-green-50 text-green-700',
	blue: 'bg-blue-50 text-blue-700',
	amber: 'bg-amber-50 text-amber-700',
	red: 'bg-red-50 text-red-700',
	gray: 'bg-gray-100 text-gray-600',
};

// KPI tile: a headline number with a tinted icon chip carrying the colour,
// while the value itself stays neutral ink (never colour-coded text).
export function StatCard({
	label,
	value,
	tone = 'blue',
	icon,
}: {
	label: string;
	value: number | string;
	tone?: BadgeTone;
	icon?: ReactNode;
}) {
	return (
		<Card className="p-5">
			{icon && (
				<div
					className={`flex h-8 w-8 items-center justify-center rounded-md ${CHIP_TONES[tone]}`}
				>
					{icon}
				</div>
			)}
			<p className="mt-3 text-2xl font-semibold tabular-nums text-gray-900">{value}</p>
			<p className="mt-1 text-sm text-gray-500">{label}</p>
		</Card>
	);
}
