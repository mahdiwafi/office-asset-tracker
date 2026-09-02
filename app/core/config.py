import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
	model_config = pydantic_settings.SettingsConfigDict(env_file='.env')
	app_name: str = 'Office Asset & Request Tracker'
	database_url: str = 'postgresql+asyncpg://tracker:tracker@localhost:5432/tracker'
	# Empty by default so tests and CI run without secrets; auth raises a
	# clear error if used without them.
	entra_tenant_id: str = ''
	entra_client_id: str = ''
	# The Application ID URI under which the SPA requests access tokens.
	# Tokens minted for the exposed API scope carry aud=api://<client_id>
	# (not the bare client id), so verify_token accepts both.
	entra_api_uri: str = ''
	# Origins allowed to call the API from the browser (the SPA dev server).
	cors_origins: list[str] = ['http://localhost:3000']
	# --- Assistant (Day 6) ---
	# Empty by default: the assistant route 503s until the container app
	# provides a search service. Generation is additionally gated on the
	# presence of the LLM API key (see app/assistant/query.py) — presence
	# of the secret IS the flag, same pattern as telemetry. The provider
	# defaults to DeepSeek (OpenAI-compatible chat completions); moving
	# providers is a base URL and a model name away (ADR 0004).
	ai_search_endpoint: str = ''
	ai_search_key: str = ''
	ai_search_index: str = 'help-docs'
	llm_api_key: str = ''
	llm_base_url: str = 'https://api.deepseek.com'
	llm_model: str = 'deepseek-v4-flash'
	embedding_model: str = 'BAAI/bge-small-en-v1.5'
	# Empty → fastembed's default cache (~/.cache/fastembed).
	embedding_cache_dir: str = ''

	@property
	def api_audience(self) -> str:
		return self.entra_api_uri or f'api://{self.entra_client_id}'


settings: Settings = Settings()
