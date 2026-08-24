# Unit tests for the chunker — the Day 6 [CP] decision, codified.
# Candidate chose target ≈400 tokens with ≈10% overlap (see ADR 0004):
# paragraph-sized chunks that fit one policy answer, with a small carried
# tail so a question straddling a chunk boundary still finds both halves.
# These tests assert the *structural* invariants (no mid-sentence cuts,
# order preserved, overlap carried, tiny tails merged) rather than exact
# arithmetic — chunk boundaries are a heuristic, not a spec.

import app.assistant.chunking as chunking


def _sentence(text: str) -> str:
	# Ensures a trailing period so the sentence splitter treats it as one.
	return text if text.endswith('.') else text + '.'


def test_estimate_tokens_four_chars_per_token():
	# Rough English ratio (≈4 chars/token). Ceiling so a chunk never
	# silently overflows its budget by rounding down.
	assert chunking.estimate_tokens('') == 0
	assert chunking.estimate_tokens('abcd') == 1
	assert chunking.estimate_tokens('abcdefgh') == 2


def test_chunk_text_empty_input_returns_empty():
	assert chunking.chunk_text('') == []
	assert chunking.chunk_text('   \n\n ') == []


def test_chunk_text_single_oversized_sentence_stays_whole():
	# A sentence larger than the target may exceed it, but must never be
	# cut in half — retrieval quality beats strict budget compliance.
	long_sentence = _sentence('word ' * 500)
	chunks = chunking.chunk_text(long_sentence, target_tokens=100)
	assert chunks == [long_sentence]


def test_chunk_text_never_splits_sentences_and_preserves_order():
	sentences = [_sentence(f'S{i:02d} ' + 'word ' * 10) for i in range(60)]
	text = ' '.join(sentences)
	chunks = chunking.chunk_text(text, target_tokens=400)
	assert len(chunks) >= 2
	seen_indexes: list[int] = []
	for chunk in chunks:
		pieces = chunking.split_sentences(chunk)
		assert pieces, 'chunk must not be empty'
		indexes = [sentences.index(piece) for piece in pieces]
		assert indexes == sorted(indexes), 'pieces must keep original order'
		seen_indexes.extend(indexes)
	assert set(seen_indexes) == set(range(60)), 'every sentence must appear somewhere'


def test_chunk_text_respects_target_size_within_sentence_slack():
	# Sentences of 10 tokens each, target 100: every chunk fits within
	# target + one sentence (the sentence that tipped it over).
	sentences = [_sentence('a' * 35 + str(i)) for i in range(80)]
	chunks = chunking.chunk_text(' '.join(sentences), target_tokens=100)
	assert len(chunks) > 1
	for chunk in chunks:
		assert chunking.estimate_tokens(chunk) <= 100 + 10


def test_chunk_text_overlap_carries_tail_of_previous_chunk():
	# 10-token sentences, target 100 → 10% overlap = 10 tokens = exactly
	# one sentence carried into the next chunk.
	sentences = [_sentence('b' * 35 + str(i)) for i in range(40)]
	chunks = chunking.chunk_text(' '.join(sentences), target_tokens=100)
	assert len(chunks) >= 3
	first_pieces = chunking.split_sentences(chunks[0])
	assert chunks[1].startswith(first_pieces[-1]), (
		'next chunk must open with the overlap tail'
	)
	assert chunks[0] != chunks[1], 'overlap must not duplicate the whole chunk'


def test_chunk_text_merges_tiny_trailing_chunk():
	# 25-token sentences, target 100 → 4 fit a chunk, the 5th is a 25-token
	# orphan (under 40% of target) — it must merge back, not stand alone.
	sentences = [_sentence('c' * 95 + str(i)) for i in range(5)]
	chunks = chunking.chunk_text(' '.join(sentences), target_tokens=100)
	assert len(chunks) == 1
	assert len(chunking.split_sentences(chunks[0])) == 5


def test_chunk_text_preserves_section_headings():
	# Headings (lines with no terminal punctuation) are their own sentence
	# units: they stay attached to the section they introduce, which keeps
	# retrieval context ("Loan periods and renewals") inside the chunk.
	text = '\n\n'.join(
		f'Section {i}\n' + ' '.join(_sentence('d' * 30 + str(j)) for j in range(12))
		for i in range(10)
	)
	chunks = chunking.chunk_text(text, target_tokens=100)
	assert chunks[0].startswith('Section 0')
	flattened = ' '.join(chunks)
	for i in range(10):
		assert f'Section {i}' in flattened, 'every heading must survive in some chunk'
