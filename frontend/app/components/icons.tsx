import type { ReactNode, SVGProps } from 'react';

// A hand-rolled 24px stroke icon set — the app needs under ten glyphs, so
// a library is a dependency we would not use. Each icon is decorative:
// it always sits next to visible text, hence aria-hidden.
function Svg({ children, ...props }: SVGProps<SVGSVGElement> & { children: ReactNode }) {
	return (
		<svg
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth={2}
			strokeLinecap="round"
			strokeLinejoin="round"
			aria-hidden="true"
			{...props}
		>
			{children}
		</svg>
	);
}

// Brand glyph: three stacked boxes, a small inventory.
export function Logo(props: SVGProps<SVGSVGElement>) {
	return (
		<Svg {...props}>
			<rect x="3" y="3" width="7" height="7" rx="1" />
			<rect x="14" y="3" width="7" height="7" rx="1" />
			<rect x="3" y="14" width="7" height="7" rx="1" />
			<rect x="14" y="14" width="7" height="7" rx="1" />
		</Svg>
	);
}

export function ArrowLeft(props: SVGProps<SVGSVGElement>) {
	return (
		<Svg {...props}>
			<path d="M19 12H5" />
			<path d="m12 19-7-7 7-7" />
		</Svg>
	);
}

export function Check(props: SVGProps<SVGSVGElement>) {
	return (
		<Svg {...props}>
			<path d="M20 6 9 17l-5-5" />
		</Svg>
	);
}

export function X(props: SVGProps<SVGSVGElement>) {
	return (
		<Svg {...props}>
			<path d="M18 6 6 18" />
			<path d="m6 6 12 12" />
		</Svg>
	);
}

export function Plus(props: SVGProps<SVGSVGElement>) {
	return (
		<Svg {...props}>
			<path d="M5 12h14" />
			<path d="M12 5v14" />
		</Svg>
	);
}

export function Info(props: SVGProps<SVGSVGElement>) {
	return (
		<Svg {...props}>
			<circle cx="12" cy="12" r="10" />
			<path d="M12 16v-4" />
			<path d="M12 8h.01" />
		</Svg>
	);
}

export function Calendar(props: SVGProps<SVGSVGElement>) {
	return (
		<Svg {...props}>
			<rect x="3" y="4" width="18" height="18" rx="2" />
			<path d="M16 2v4" />
			<path d="M8 2v4" />
			<path d="M3 10h18" />
		</Svg>
	);
}

export function Box(props: SVGProps<SVGSVGElement>) {
	return (
		<Svg {...props}>
			<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
			<path d="m3.3 7 8.7 5 8.7-5" />
			<path d="M12 22V12" />
		</Svg>
	);
}

// Busy indicator. Not part of the Svg wrapper: it needs fill and its own
// animation. Callers set size and colour via className.
export function Spinner(props: SVGProps<SVGSVGElement>) {
	return (
		<svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="animate-spin" {...props}>
			<circle
				className="opacity-25"
				cx="12"
				cy="12"
				r="10"
				stroke="currentColor"
				strokeWidth="4"
			/>
			<path
				className="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"
			/>
		</svg>
	);
}
