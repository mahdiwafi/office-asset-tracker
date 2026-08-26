import Link from 'next/link';
import type { ReactNode } from 'react';

import { Spinner } from './icons';

const VARIANTS = {
	primary: 'bg-blue-700 text-white hover:bg-blue-800',
	success: 'bg-green-700 text-white hover:bg-green-800',
	danger: 'bg-red-700 text-white hover:bg-red-800',
	secondary: 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50',
} as const;

export function Button({
	variant = 'primary',
	type = 'button',
	disabled,
	busy = false,
	onClick,
	href,
	title,
	children,
}: {
	variant?: keyof typeof VARIANTS;
	type?: 'button' | 'submit';
	disabled?: boolean;
	busy?: boolean;
	onClick?: () => void;
	// Render as a next/link with the button's styling instead of a <button>.
	href?: string;
	// Native tooltip, e.g. to explain why a lifecycle action is disabled.
	title?: string;
	children: ReactNode;
}) {
	const classes = `inline-flex items-center gap-1.5 rounded-md px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]}`;
	if (href) {
		return (
			<Link href={href} title={title} className={classes}>
				{busy && <Spinner className="h-4 w-4" />}
				{children}
			</Link>
		);
	}
	return (
		<button
			type={type}
			onClick={onClick}
			disabled={disabled || busy}
			title={title}
			className={classes}
		>
			{busy && <Spinner className="h-4 w-4" />}
			{children}
		</button>
	);
}
