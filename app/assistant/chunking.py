# The chunker: splits an article into retrieval-sized chunks.
#
# The Day 6 [CP] decision, codified here and recorded in ADR 0004: the
# candidate chose target ≈400 tokens with ≈10% overlap. 400 tokens is
# roughly one policy paragraph — small enough that a chunk answers one
# question, large enough that an answer rarely spans chunks. The 10%
# overlap carries a short tail into the next chunk so a question that
# straddles a boundary still finds both halves.
#
# Token count is estimated as chars / 4 — the standard English ratio. A
# real tokenizer would be more precise, but precision here is a heuristic
# anyway; what matters is that chunks are sentence-complete (a cut
# sentence destroys retrieval for both halves) and roughly uniform.
import math
import re

CHUNK_TARGET_TOKENS = 400
CHUNK_OVERLAP = 0.10


def estimate_tokens(text: str) -> int:
	"""Rough English token count: ≈4 characters per token."""
	return math.ceil(len(text) / 4)


def split_sentences(text: str) -> list[str]:
	"""Split on sentence endings. Heading lines (no terminal punctuation)
	stay whole — they are their own unit and attach to the sentence that
	follows them, which is exactly the context retrieval wants."""
	return [
		piece.strip()
		for piece in re.split(r'(?<=[.!?])\s+', text.strip())
		if piece.strip()
	]


def chunk_text(
	text: str,
	*,
	target_tokens: int = CHUNK_TARGET_TOKENS,
	overlap: float = CHUNK_OVERLAP,
) -> list[str]:
	"""Split an article into overlapping, sentence-complete chunks.

	Sentences accumulate until the target is reached; the chunk then
	closes and the next one re-opens with the tail of the previous chunk
	(up to `overlap` of the target). A trailing chunk under 40% of the
	target merges back into the previous one — an orphan sentence chunk
	helps nobody — and because the trailing chunk opens with the previous
	chunk's overlap tail, the merge drops that carried prefix rather than
	duplicating it. A single sentence larger than the target is kept whole.
	"""
	if not text.strip():
		return []
	sentences = split_sentences(text)
	overlap_tokens = int(target_tokens * overlap)
	# (pieces, carried_sentences_at_start): the carry count lets the
	# merge step drop a trailing chunk's overlap prefix — it is already
	# present in the previous chunk.
	chunks: list[tuple[list[str], int]] = []
	current: list[str] = []
	current_tokens = 0
	opening_carry = 0
	for sentence in sentences:
		tokens = estimate_tokens(sentence)
		if current_tokens + tokens > target_tokens and current:
			chunks.append((current, opening_carry))
			# Carry the chunk's tail into the next chunk: walk backwards
			# while the carried tail fits the overlap budget.
			carry: list[str] = []
			carry_tokens = 0
			for previous in reversed(current):
				if carry_tokens + estimate_tokens(previous) > overlap_tokens:
					break
				carry.insert(0, previous)
				carry_tokens += estimate_tokens(previous)
			current = list(carry)
			current_tokens = carry_tokens
			opening_carry = len(carry)
		current.append(sentence)
		current_tokens += tokens
	if current:
		chunks.append((current, opening_carry))
	if (
		len(chunks) >= 2
		and estimate_tokens(' '.join(chunks[-1][0])) < target_tokens * 0.4
	):
		tail_pieces, carried = chunks.pop()
		chunks[-1] = (chunks[-1][0] + tail_pieces[carried:], chunks[-1][1])
	return [' '.join(pieces) for pieces, _ in chunks]
