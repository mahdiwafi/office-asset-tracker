// MSAL configuration for the asset tracker SPA. The client id and tenant
// id come from the environment (NEXT_PUBLIC_* is baked into the client
// bundle — that is expected for a public SPA; the API trusts the token,
// never the app).
import { PublicClientApplication, type Configuration } from '@azure/msal-browser';

const clientId = process.env.NEXT_PUBLIC_ENTRA_CLIENT_ID ?? '';
const tenantId = process.env.NEXT_PUBLIC_ENTRA_TENANT_ID ?? '';

// The redirect URI must be the origin the user is actually on: localhost
// in development, the deployed URL in production. Baking one value would
// break the other environment, so derive it at runtime and let an env
// override win when one exists.
const redirectUri =
	process.env.NEXT_PUBLIC_REDIRECT_URI ??
	(typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000');

export const msalConfig: Configuration = {
	auth: {
		clientId,
		authority: `https://login.microsoftonline.com/${tenantId}`,
		redirectUri,
	},
	cache: { cacheLocation: 'localStorage' },
};

// The scope the API exposes (Expose an API -> access_as_user). Tokens for
// this scope carry aud=api://<client_id>, which the API accepts.
export const loginRequest = {
	scopes: [`api://${clientId}/access_as_user`],
};

export const msalInstance = new PublicClientApplication(msalConfig);
