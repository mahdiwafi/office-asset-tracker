'use client';

import { AuthenticatedTemplate, UnauthenticatedTemplate } from '@azure/msal-react';
import type { ReactNode } from 'react';

import { LoginButton } from './login-button';

// The client-side gate. The API enforces the real rules server-side;
// this only decides which screens to show.
export function RequireAuth({ children }: { children: ReactNode }) {
	return (
		<>
			<AuthenticatedTemplate>{children}</AuthenticatedTemplate>
			<UnauthenticatedTemplate>
				<main className="mx-auto max-w-xl px-4 py-24 text-center">
					<h1 className="mb-2 text-2xl font-semibold">Office Asset Tracker</h1>
					<p className="mb-8 text-gray-600">
						Internal tool for equipment, loans, and requests.
					</p>
					<LoginButton />
				</main>
			</UnauthenticatedTemplate>
		</>
	);
}
