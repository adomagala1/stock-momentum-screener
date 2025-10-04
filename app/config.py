import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Mongo
    mongo_uri: str
    mongo_db: str

    # Postgres
    pg_user: str
    pg_password: str
    pg_host: str
    pg_port: int
    pg_db: str

    # Supabase
    sb_url: str
    sb_api: str
    sb_password: str

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'),
        env_file_encoding='utf-8',
        env_prefix="",
        extra="ignore",
        fields={
            'sb_url': {'env': 'SUPABASE_URL'},
            'sb_api': {'env': 'SUPABASE_KEY'},
            'sb_password': {'env': 'SB_PASSWORD'}
        }
    )

settings = Settings()
