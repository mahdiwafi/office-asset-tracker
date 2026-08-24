"""Run the Day 7 golden set against the live retrieval and generation stack.

The ADR 0005 point, in one command: retrieval quality and generation are
probabilistic, so the unit suite proves wiring, not answers — and this
script is the manual tripwire for quality. It runs the ten evaluation
pairs from docs/golden-set.md against the real services and prints a
transcript to grade by hand.

Retrieval needs AI_SEARCH_ENDPOINT and AI_SEARCH_KEY. Generation (and
therefore the refusal path) additionally needs LLM_API_KEY — without it
the script prints what retrieval found and skips the answer, because a
citations-only run would not be a fair sample of the deployed behaviour
(the container runs with the key).

Run: uv run python -m scripts.golden_set
"""

import os

from app.assistant.query import answer_question

# (category, question, expected articles in top-5; empty = noise is fine)
GOLDEN_SET: list[tuple[str, str, list[str]]] = [
	('exact', 'How long can I borrow a laptop?', ['loan-periods']),
	('exact', 'What do I return when I leave the company?', ['offboarding-returns']),
	(
		'paraphrase',
		'I am flying abroad for a client workshop — can I take the projector with me?',
		['asset-care'],
	),
	(
		'paraphrase',
		'How do I get a second monitor for report writing?',
		['requesting-equipment'],
	),
	('fuzzy', 'My laptop screen is cracked, what should I do?', ['damage-and-loss']),
	('paraphrase', 'Can I keep a headset for the whole project?', ['loan-periods']),
	(
		'eligibility',
		'Who gets a camera when several people want one?',
		['eligibility-and-priority'],
	),
	('near-miss', 'What time does the office open?', []),
	('out-of-scope', 'What is the capital of France?', []),
	('nonsense', 'zzzzqqqq', []),
]


def main() -> None:
	has_key = bool(os.environ.get('LLM_API_KEY'))
	print(
		f'golden set: {len(GOLDEN_SET)} queries, generation '
		f'{"ON" if has_key else "OFF (LLM_API_KEY missing — retrieval only)"}'
	)
	for number, (category, question, expected) in enumerate(GOLDEN_SET, start=1):
		print(f'\n[{number}] {category:11s} {question!r}')
		answer = answer_question(question)
		print(f'    configured={answer.generation_configured} refused={answer.refused}')
		if not answer.citations:
			print('    retrieval: no results')
		else:
			top = answer.citations[0]
			scores = ' '.join(
				f'{c.article_slug}={c.score:.4f}' for c in answer.citations
			)
			if not expected:
				print(
					f'    retrieval: {top.article_slug} (no expected article — noise is fine)'
				)
			else:
				hit = any(c.article_slug in expected for c in answer.citations)
				print(
					f'    retrieval: {top.article_slug} | {scores} | {"HIT" if hit else "MISS"}'
				)
		if answer.answer:
			print(f'    answer: {answer.answer}')
		elif has_key:
			print('    answer: (none — grade the refusal against docs/golden-set.md)')
		else:
			print(
				'    answer: (skipped — rerun with LLM_API_KEY for the generation leg)'
			)


if __name__ == '__main__':
	main()
