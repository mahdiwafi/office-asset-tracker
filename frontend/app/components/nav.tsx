'use client';

import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import Link from 'next/link';

const links = [
	{ href: '/', label: 'Assets' },
	{ href: '/requests/new', label: 'Raise request' },
	{ href: '/approvals', label: 'Approvals' },
	{ href: '/loans', label: 'My loans' },
	{ href: '/audit', label: 'Audit log' },
	{ href: '/assistant', label: 'Ask ICT' },
];

export function Nav() {
	const isAuthenticated = useIsAuthenticated();
	const { instance, accounts } = useMsal();
	// Derived from hook state instead of an effect: accounts updates when
	// the auth state changes, which re-renders this component anyway.
	const name = accounts[0]?.name ?? accounts[0]?.username ?? null;

	if (!isAuthenticated) return null;

	return (
		<header className="border-b border-gray-200 bg-white">
			<nav className="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
				<span className="font-semibold">Asset Tracker</span>
				{links.map((link) => (
					<Link key={link.href} href={link.href} className="text-sm text-gray-700 hover:underline">
						{link.label}
					</Link>
				))}
				<span className="ml-auto text-sm text-gray-500">{name}</span>
				<button
					onClick={() =>
						instance.logoutRedirect({ postLogoutRedirectUri: window.location.origin })
					}
					className="text-sm text-gray-500 hover:underline"
				>
					Sign out
				</button>
			</nav>
		</header>
	);
}
