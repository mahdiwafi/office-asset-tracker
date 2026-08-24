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
	# answer is None when generation is not configured (no API key) or
	# when nothing relevant was retrieved — the client shows the
	# citations either way. generation_configured lets the client explain
	# WHY there is no answer instead of pretending.
	answer: str | None = None
	generation_configured: bool = False
	citations: list[Citation] = []
