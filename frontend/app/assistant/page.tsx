'use client';

import { FormEvent, useState } from 'react';

import { ApiError, api } from '@/lib/api';
import { RequireAuth } from '../components/require-auth';

// The help articles live in the repo (docs/help) and the repo is public —
// every citation links back to its source of truth instead of ending at a
// black-box answer.
const HELP_DOCS_BASE = 'https://github.com/mahdiwafi/office-asset-tracker/blob/main/docs/help';

type Citation = {
	article_title: string;
	article_slug: string;
	chunk_index: number;
	excerpt: string;
	score: number;
};

type AssistantAnswer = {
	answer: string | null;
	generation_configured: boolean;
	refused: boolean;
	citations: Citation[];
};

// The answer cites its sources as [1], [2]… matching the numbered chunk
// list below. Render each marker as a link to its source card instead of
// raw text — the citation trail is the whole point of this page.
function renderAnswer(answer: string) {
	const parts = answer.split(/(\[\d+\])/);
	return parts.map((part, index) => {
		const marker = /^\[(\d+)\]$/.exec(part);
		if (!marker) return part;
		return (
			<sup key={index}>
				<a href={`#citation-${marker[1]}`} className="text-blue-700 hover:underline">
					[{marker[1]}]
				</a>
			</sup>
		);
	});
}

function ResultView({ result }: { result: AssistantAnswer }) {
	return (
		<div className="mt-6 space-y-4">
			{result.answer ? (
				<div className="rounded border border-green-200 bg-green-50 p-4 text-sm leading-relaxed">
					<p className="font-medium text-green-900">Answer</p>
					<p className="mt-1 whitespace-pre-wrap text-green-900">
						{renderAnswer(result.answer)}
					</p>
				</div>
			) : result.refused ? (
				<div className="rounded border border-amber-200 bg-amber-50 p-4 text-sm">
					<p className="font-medium text-amber-900">
						I couldn&apos;t find an answer to that in our policies.
					</p>
					<p className="mt-1 text-amber-800">
						The evidence below was too weak to answer from — contact ICT if this looks
						wrong.
					</p>
				</div>
			) : !result.generation_configured && result.citations.length > 0 ? (
				<div className="rounded border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
					Answer generation isn&apos;t configured — showing the policies that match instead.
				</div>
			) : null}
			{result.citations.length === 0 ? (
				<p className="text-sm text-gray-500">
					No matching policies found. Try rephrasing — e.g. &quot;how long can I borrow a
					laptop?&quot;
				</p>
			) : (
				<section aria-label="Cited sources">
					<h2 className="mb-2 text-sm font-semibold text-gray-700">
						Cited sources ({result.citations.length})
					</h2>
					<ol className="space-y-2">
						{result.citations.map((citation, index) => (
							<li
								key={`${citation.article_slug}-${citation.chunk_index}`}
								id={`citation-${index + 1}`}
								className="rounded border border-gray-200 bg-white p-3 text-sm"
							>
								<a
									href={`${HELP_DOCS_BASE}/${citation.article_slug}.md`}
									target="_blank"
									rel="noreferrer"
									className="font-medium text-blue-700 hover:underline"
								>
									{index + 1}. {citation.article_title}
								</a>
								<p className="mt-1 text-gray-600">{citation.excerpt}</p>
								<p className="mt-1 font-mono text-xs text-gray-400">
									chunk {citation.chunk_index} · match {citation.score.toFixed(4)}
								</p>
							</li>
						))}
					</ol>
				</section>
			)}
		</div>
	);
}

export default function AssistantPage() {
	const [question, setQuestion] = useState('');
	const [asking, setAsking] = useState(false);
	const [result, setResult] = useState<AssistantAnswer | null>(null);
	const [error, setError] = useState<string | null>(null);

	async function handleSubmit(e: FormEvent) {
		e.preventDefault();
		if (!question.trim()) return;
		setAsking(true);
		setError(null);
		setResult(null);
		try {
			const body = await api('/assistant/query', {
				method: 'POST',
				body: { question },
			});
			setResult(body);
		} catch (err) {
			setError(err instanceof ApiError ? err.message : String(err));
		} finally {
			setAsking(false);
		}
	}

	return (
		<RequireAuth>
			<main className="mx-auto max-w-3xl px-4 py-8">
				<h1 className="mb-1 text-xl font-semibold">Ask ICT</h1>
				<p className="mb-4 text-sm text-gray-600">
					Answers come from our help docs — every claim cites the policy it came from.
				</p>
				{error && <p className="mb-4 text-red-700">{error}</p>}
				<form onSubmit={handleSubmit} className="flex gap-2">
					<input
						value={question}
						onChange={(e) => setQuestion(e.target.value)}
						placeholder="How long can I borrow a laptop?"
						className="w-full rounded border border-gray-300 px-3 py-2 text-sm"
					/>
					<button
						type="submit"
						disabled={asking || !question.trim()}
						className="shrink-0 rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
					>
						{asking ? 'Searching…' : 'Ask'}
					</button>
				</form>
				{asking && (
					<p className="mt-4 text-sm text-gray-500">
						Searching the help docs — this can take a few seconds…
					</p>
				)}
				{result && <ResultView result={result} />}
			</main>
		</RequireAuth>
	);
}
