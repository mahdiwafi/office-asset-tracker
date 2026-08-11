import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
	model_config = pydantic_settings.SettingsConfigDict(env_file='.env')
	app_name: str = 'Office Asset & Request Tracker'
	database_url: str = 'postgresql+asyncpg://tracker:tracker@localhost:5432/tracker'


settings: Settings = Settings()
