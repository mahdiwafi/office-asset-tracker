import pydantic


class AssistantQuery(pydantic.BaseModel):
	question: str = pydantic.Field(
		min_length=1, max_length=500, examples=['How long can I borrow a laptop?']
	)


class Citation(pydantic.BaseModel):
	article_title: str
	article_slug: str
	chunk_index: int
	excerpt: str
	score: float


class AssistantAnswer(pydantic.BaseModel):
	# answer is None when generation is not configured (no API key), was
	# refused below the score floor, or failed — the client shows the
	# citations either way. generation_configured lets the client explain
	# WHY there is no answer instead of pretending. refused marks the
	# deliberate below-floor refusal (Day 7 [CP]): evidence was retrieved
	# but too weak to answer from, so generation was skipped on purpose.
	answer: str | None = None
	generation_configured: bool = False
	refused: bool = False
	citations: list[Citation] = []
