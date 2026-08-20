'use client';

import { InteractionStatus } from '@azure/msal-browser';
import { useMsal } from '@azure/msal-react';
import { useState } from 'react';

import { loginRequest } from '@/lib/msal';

// Redirect flow: the whole tab goes to Microsoft and comes back with the
// response in the URL; MsalProvider completes the handshake on the way in.
// Unlike a popup there is no cross-window handshake to break, nothing for a
// popup blocker to swallow, and no nested-popup race.
export function LoginButton() {
	const { instance, inProgress } = useMsal();
	const [error, setError] = useState<string | null>(null);
	const busy = inProgress !== InteractionStatus.None;

	async function handleSignIn() {
		setError(null);
		try {
			await instance.loginRedirect(loginRequest);
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		}
	}

	return (
		<div>
			<button
				onClick={handleSignIn}
				disabled={busy}
				className="rounded bg-blue-700 px-4 py-2 font-medium text-white hover:bg-blue-800 disabled:opacity-50"
			>
				{busy ? 'Redirecting to sign-in…' : 'Sign in with your organisation account'}
			</button>
			{error && <p className="mt-4 text-sm text-red-700">{error}</p>}
		</div>
	);
}
