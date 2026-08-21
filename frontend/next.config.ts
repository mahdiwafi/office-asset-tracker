import type { NextConfig } from 'next';

// standalone output bundles the server and its minimal node_modules into
// .next/standalone — what App Service's Node runtime starts with
// `node server.js` instead of a dev-server-shaped process.
const nextConfig: NextConfig = {
	output: 'standalone',
};

export default nextConfig;
