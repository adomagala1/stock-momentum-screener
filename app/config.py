import os
from pydantic_settings import BaseSettings

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

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), '..', '.env')
        extra = "ignore"

settings = Settings()
