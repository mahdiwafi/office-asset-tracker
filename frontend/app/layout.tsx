import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';

import { Nav } from './components/nav';
import { AuthProvider } from './providers';
import './globals.css';

const geistSans = Geist({
	variable: '--font-geist-sans',
	subsets: ['latin'],
});

const geistMono = Geist_Mono({
	variable: '--font-geist-mono',
	subsets: ['latin'],
});

export const metadata: Metadata = {
	title: 'Office Asset Tracker',
	description: 'Internal ICT equipment, loans, and requests',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
	return (
		<html
			lang="en"
			className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
		>
			<body className="min-h-full flex flex-col bg-gray-50">
				<AuthProvider>
					<Nav />
					{children}
				</AuthProvider>
			</body>
		</html>
	);
}
