from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    SLEEP_TIME: list[int] = [3000, 4000]
    START_DELAY: list[int] = [5, 25]
    NIGHT_SLEEP: bool = True
    NIGHT_SLEEP_START_TIME: list[int] = [0, 2]
    NIGHT_SLEEP_END_TIME: list[int] = [5, 7]
    AUTO_MINING: bool = True
    AUTO_UPGRADE: bool = True
    MIN_STARS: int = 100
    USE_BOOSTS: bool = False
    REF_ID: str = 'galaxy-00042498770002d6ddec0000a9a392'
    TOKENS_PATH: str = 'session_tokens.json'


settings = Settings()
