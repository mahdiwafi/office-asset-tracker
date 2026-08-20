// The one place the frontend talks to the API: acquires an access token
// for the API scope (silent, falling back to a popup) and attaches it as
// a bearer token. Every screen goes through this, so there is no route
// that can accidentally call the API unauthenticated.
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

async function acquireToken(): Promise<string> {
	try {
		const response = await msalInstance.acquireTokenSilent(loginRequest);
		return response.accessToken;
	} catch {
		// Silent acquisition failed (new session, consent needed) — pop up
		// the sign-in window so the user can complete the flow.
		const response = await msalInstance.acquireTokenPopup(loginRequest);
		return response.accessToken;
	}
}

type ApiOptions = Omit<RequestInit, 'body'> & {
	// The API speaks JSON: the wrapper stringifies whatever object the
	// caller passes instead of letting fetch treat it as raw BodyInit.
	body?: unknown;
};

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
