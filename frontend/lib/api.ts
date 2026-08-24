// The one place the frontend talks to the API: acquires an access token
// for the API scope (silent, falling back to a sign-in redirect) and
// attaches it as a bearer token. Every screen goes through this, so there
// is no route that can accidentally call the API unauthenticated.
import { InteractionRequiredAuthError } from '@azure/msal-browser';

import { msalInstance, loginRequest } from './msal';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string,
	) {
		super(message);
	}
}

// The app signs in with the redirect flow, so the first token request on a
// fresh page load can race the redirect response MsalProvider is still
// processing. Wait for it to settle: once it has, the tokens are in the
// cache and silent acquisition works.
const msalReady = msalInstance
	.initialize()
	.then(() => msalInstance.handleRedirectPromise())
	.catch(() => null);

let redirectStarted = false;

// Send the whole tab through sign-in. Guarded so a failing flow can't
// redirect in a loop.
function startRedirect() {
	if (redirectStarted) return;
	redirectStarted = true;
	msalInstance.loginRedirect(loginRequest).catch((redirectErr) => {
		// Don't let a swallowed redirect hide the failure.
		console.warn('loginRedirect failed:', redirectErr);
	});
}

async function acquireToken(): Promise<string> {
	await msalReady;
	// Silent acquisition needs an account bound to the request. The account
	// is in the cache, but getActiveAccount() is often unset — fall back to
	// the first cached account explicitly, and make it the active one so
	// the rest of the app agrees on who is signed in.
	const account = msalInstance.getActiveAccount() ?? msalInstance.getAllAccounts()[0];
	if (!account) {
		startRedirect();
		throw new Error('Sign-in is starting — the page will reload when it finishes.');
	}
	msalInstance.setActiveAccount(account);
	try {
		const response = await msalInstance.acquireTokenSilent({
			...loginRequest,
			account,
		});
		return response.accessToken;
	} catch (err) {
		// Distinguish "the user needs to go sign in again" (interaction-
		// required — the right response is a redirect) from a broken
		// request (missing scope, consent misconfiguration — the right
		// response is to surface the real error, not bounce in a loop).
		const code =
			typeof err === 'object' && err !== null && 'errorCode' in err
				? (err as { errorCode: string }).errorCode
				: undefined;
		const needsInteraction =
			err instanceof InteractionRequiredAuthError ||
			code === 'interaction_required' ||
			code === 'login_required' ||
			code === 'consent_required' ||
			code === 'no_account_in_silent_request';
		if (needsInteraction) {
			startRedirect();
			throw new Error('Sign-in is starting — the page will reload when it finishes.');
		}
		throw err instanceof Error ? err : new Error(String(err));
	}
}

type ApiOptions = Omit<RequestInit, 'body'> & {
	// The API speaks JSON: the wrapper stringifies whatever object the
	// caller passes instead of letting fetch treat it as raw BodyInit.
	body?: unknown;
};

// The API speaks JSON whose shape varies by endpoint; every caller
// narrows the fields it needs, so the wrapper's return type is
// deliberately loose.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function api(path: string, options: ApiOptions = {}): Promise<any> {
	const token = await acquireToken();
	const response = await fetch(`${API_BASE}${path}`, {
		...options,
		body: options.body === undefined ? undefined : JSON.stringify(options.body),
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json',
			...(options.headers ?? {}),
		},
	});
	if (!response.ok) {
		const body = await response.json().catch(() => null);
		throw new ApiError(
			response.status,
			typeof body?.detail === 'string' ? body.detail : `HTTP ${response.status}`,
		);
	}
	return response.status === 204 ? null : response.json();
}
