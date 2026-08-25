'use client';

import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { Logo } from './icons';

const links = [
	{ href: '/', label: 'Assets' },
	{ href: '/requests/new', label: 'Raise request' },
	{ href: '/approvals', label: 'Approvals' },
	{ href: '/loans', label: 'My loans' },
	{ href: '/audit', label: 'Audit log' },
	{ href: '/assistant', label: 'Ask ICT' },
];

function initials(name: string): string {
	const words = name.trim().split(/\s+/);
	const letters = words.slice(0, 2).map((w) => w[0] ?? '');
	return letters.join('').toUpperCase() || '?';
}

export function Nav() {
	const isAuthenticated = useIsAuthenticated();
	const { instance, accounts } = useMsal();
	// Derived from hook state instead of an effect: accounts updates when
	// the auth state changes, which re-renders this component anyway.
	const name = accounts[0]?.name ?? accounts[0]?.username ?? null;
	const pathname = usePathname();
	const isActive = (href: string) =>
		href === '/' ? pathname === '/' : pathname.startsWith(href);

	if (!isAuthenticated) return null;

	return (
		<header className="sticky top-0 z-10 border-b border-gray-200 bg-white">
			<nav className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-3">
				<Link href="/" className="mr-2 flex items-center gap-2">
					<span className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-700 text-white">
						<Logo className="h-4 w-4" />
					</span>
					<span className="font-semibold text-gray-900">Asset Tracker</span>
				</Link>
				{links.map((link) => (
					<Link
						key={link.href}
						href={link.href}
						className={`rounded-md px-3 py-1.5 text-sm font-medium ${
							isActive(link.href)
								? 'bg-gray-100 text-gray-900'
								: 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
						}`}
					>
						{link.label}
					</Link>
				))}
				<div className="ml-auto flex items-center gap-3">
					{name && (
						<>
							<span className="flex h-7 w-7 items-center justify-center rounded-full bg-blue-700 text-xs font-medium text-white">
								{initials(name)}
							</span>
							<span className="text-sm text-gray-700">{name}</span>
						</>
					)}
					<button
						onClick={() =>
							instance.logoutRedirect({ postLogoutRedirectUri: window.location.origin })
						}
						className="rounded-md px-2 py-1 text-sm text-gray-500 hover:bg-gray-50 hover:text-gray-900"
					>
						Sign out
					</button>
				</div>
			</nav>
		</header>
	);
}
