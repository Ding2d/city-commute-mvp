from typing import Literal
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="COMMUTE_", env_file=".env", extra="ignore")

    output_dir: Path = Path("outputs")
    route_count: int = Field(4, ge=3, le=5)
    sentence_count: int = Field(6, ge=1, le=12)
    min_chars: int = Field(20, ge=10, le=80)
    max_chars: int = Field(30, ge=10, le=80)
    data_provider: Literal["mock", "osm_wikidata"] = "mock"
    llm_provider: Literal["mock", "openai_compatible"] = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    llm_timeout_seconds: float = Field(30, gt=0, le=120)
    llm_format_retries: int = Field(1, ge=0, le=3)
    llm_temperature: float = Field(0.7, ge=0, le=2)
    llm_max_tokens: int = Field(1200, ge=100, le=8000)
    score_landmark_weight: float = Field(0.5, ge=0, le=1)
    score_scenario_weight: float = Field(0.3, ge=0, le=1)
    score_friction_weight: float = Field(0.2, ge=0, le=1)

    @model_validator(mode="after")
    def validate_settings(self):
        if self.min_chars > self.max_chars:
            raise ValueError("min_chars must not exceed max_chars")
        if self.score_landmark_weight + self.score_scenario_weight + self.score_friction_weight <= 0:
            raise ValueError("at least one scoring weight must be positive")
        if self.llm_provider == "openai_compatible":
            if not self.llm_api_key.get_secret_value() or not self.llm_model.strip():
                raise ValueError("real LLM requires COMMUTE_LLM_API_KEY and COMMUTE_LLM_MODEL")
            if not self.llm_base_url.startswith(("https://", "http://")):
                raise ValueError("LLM base URL must be HTTP(S)")
        return self
