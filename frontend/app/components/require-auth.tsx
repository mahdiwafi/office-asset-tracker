'use client';

import { AuthenticatedTemplate, UnauthenticatedTemplate } from '@azure/msal-react';
import type { ReactNode } from 'react';

import { Card } from './card';
import { Logo } from './icons';
import { LoginButton } from './login-button';

// The client-side gate. The API enforces the real rules server-side;
// this only decides which screens to show.
export function RequireAuth({ children }: { children: ReactNode }) {
	return (
		<>
			<AuthenticatedTemplate>{children}</AuthenticatedTemplate>
			<UnauthenticatedTemplate>
				<main className="mx-auto flex w-full max-w-md flex-col items-center px-4 py-24 text-center">
					<Card className="w-full p-10">
						<div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-700 text-white">
							<Logo className="h-6 w-6" />
						</div>
						<h1 className="mt-4 text-2xl font-semibold tracking-tight text-gray-900">
							Office Asset Tracker
						</h1>
						<p className="mt-2 text-sm text-gray-500">
							Internal tool for equipment, loans, and requests.
						</p>
						<div className="mt-6">
							<LoginButton />
						</div>
					</Card>
					<p className="mt-6 text-xs text-gray-400">
						Single sign-on via Microsoft Entra ID
					</p>
				</main>
			</UnauthenticatedTemplate>
		</>
	);
}
