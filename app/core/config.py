from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DB_TYPE: str = "sqlite"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "fitness_studio"
    DB_PATH: str = "./fitness_studio.db"

    SECRET_KEY: str = "fitness-studio-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ADMIN_PHONE: str = "13800138000"
    ADMIN_PASSWORD: str = "admin123456"

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE.lower() == "mysql":
            return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        else:
            return f"sqlite:///{self.DB_PATH}"


settings = Settings()
