import type { ReactNode } from 'react';

export function PageHeader({
	title,
	description,
	children,
}: {
	title: string;
	description?: string;
	children?: ReactNode;
}) {
	return (
		<div className="mb-6 flex items-start justify-between gap-4">
			<div>
				<h1 className="text-2xl font-semibold tracking-tight text-gray-900">{title}</h1>
				{description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
			</div>
			{children}
		</div>
	);
}
