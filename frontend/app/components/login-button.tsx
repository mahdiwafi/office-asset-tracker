'use client';

import { InteractionStatus } from '@azure/msal-browser';
import { useMsal } from '@azure/msal-react';
import { useState } from 'react';

import { loginRequest } from '@/lib/msal';

// MSAL refuses to open a second popup while it thinks a flow is running
// (block_nested_popups). That happens when the button is clicked twice, or
// when a previous attempt was interrupted — a blocked popup, or a dev-server
// restart mid-flow — leaving stale "in progress" state in sessionStorage,
// which survives page reloads. The button disables while a flow is running,
// and a stale-flow error clears the temporary state so the next click works.
function isBlockedNestedPopups(err: unknown): boolean {
	return (
		typeof err === 'object' &&
		err !== null &&
		'errorCode' in err &&
		(err as { errorCode: string }).errorCode === 'block_nested_popups'
	);
}

export function LoginButton() {
	const { instance, inProgress } = useMsal();
	const [error, setError] = useState<string | null>(null);
	const busy = inProgress !== InteractionStatus.None;

	async function handleSignIn() {
		setError(null);
		try {
			await instance.loginPopup(loginRequest);
		} catch (err) {
			if (isBlockedNestedPopups(err)) {
				// A previous flow never finished. Temporary keys (the flow
				// state) live in sessionStorage; persistent keys (accounts)
				// live in localStorage and are left alone.
				Object.keys(sessionStorage)
					.filter((key) => key.startsWith('msal.'))
					.forEach((key) => sessionStorage.removeItem(key));
				setError(
					'Sign-in was interrupted. The stale flow state has been cleared — please try again.',
				);
				return;
			}
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
				{busy ? 'Signing in…' : 'Sign in with your organisation account'}
			</button>
			{error && <p className="mt-4 text-sm text-red-700">{error}</p>}
		</div>
	);
}
