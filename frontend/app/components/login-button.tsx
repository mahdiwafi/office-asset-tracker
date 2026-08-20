'use client';

import { useMsal } from '@azure/msal-react';

import { loginRequest } from '@/lib/msal';

export function LoginButton() {
	const { instance } = useMsal();
	return (
		<button
			onClick={() => instance.loginPopup(loginRequest)}
			className="rounded bg-blue-700 px-4 py-2 font-medium text-white hover:bg-blue-800"
		>
			Sign in with your organisation account
		</button>
	);
}
