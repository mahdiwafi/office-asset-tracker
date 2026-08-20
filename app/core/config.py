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

	@property
	def api_audience(self) -> str:
		return self.entra_api_uri or f'api://{self.entra_client_id}'


settings: Settings = Settings()
