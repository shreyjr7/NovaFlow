import os
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings  # type: ignore
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    DATABASE_URL: str = Field(
        os.environ.get(
            'DATABASE_URL',
            os.environ.get('SUPABASE_DB_URL', 'sqlite:///./novaflow.db')
        ),
        env='DATABASE_URL'
    )
    JWT_SECRET_KEY: SecretStr = Field(SecretStr('novaflow-secret-key-dev-123456789'), env='JWT_SECRET_KEY')
    JWT_ALGORITHM: str = Field('HS256', env='JWT_ALGORITHM')
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env='ACCESS_TOKEN_EXPIRE_MINUTES')
    RATE_LIMIT_PER_MIN: int = Field(100, env='RATE_LIMIT_PER_MIN')
    LOG_LEVEL: str = Field('info', env='LOG_LEVEL')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'
