"""Application configuration — prototype economic parameters are configurable."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "GRIDFLEX Pakistan"
    app_subtitle: str = "Turn unused electricity flexibility into value."
    secret_key: str = "gridflex-pakistan-dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12
    database_url: str = "sqlite:///./gridflex.db"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://*.vercel.app"
    )

    # Prototype economic model (NOT real Pakistani tariffs)
    platform_fee_pct: float = 0.05
    grid_fee_pct: float = 0.02
    normal_price_pkr: float = 8.0
    peak_price_pkr: float = 15.0
    critical_price_pkr: float = 25.0

    # Simulation defaults
    sim_households: int = 10_000
    sim_commercial: int = 1_000
    sim_industrial: int = 100
    sim_solar: int = 2_000
    sim_batteries: int = 500

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()