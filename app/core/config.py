import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
	model_config = pydantic_settings.SettingsConfigDict(env_file='.env')
	app_name: str = 'Office Asset & Request Tracker'
	database_url: str = 'postgresql+asyncpg://tracker:tracker@localhost:5432/tracker'
	# Empty by default so tests and CI run without secrets; auth raises a
	# clear error if used without them.
	entra_tenant_id: str = ''
	entra_client_id: str = ''


settings: Settings = Settings()
