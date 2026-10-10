import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NarrativeOptions(InputModel):
    sentence_count: int = Field(6, ge=1, le=12)
    min_chars: int = Field(20, ge=10, le=80)
    max_chars: int = Field(30, ge=10, le=80)

    @model_validator(mode="after")
    def validate_range(self):
        if self.min_chars > self.max_chars:
            raise ValueError("min_chars must not exceed max_chars")
        return self


class CommuteRequest(InputModel):
    city: str = Field(min_length=1, max_length=40)
    route_count: int | None = Field(None, ge=3, le=5)
    narrative: NarrativeOptions | None = None

    @field_validator("city")
    @classmethod
    def normalize_city(cls, value: str) -> str:
        value = value.strip()
        if value.endswith("市"):
            value = value[:-1]
        if not re.fullmatch(r"[\u4e00-\u9fff]{2,20}", value):
            raise ValueError("请输入二至二十个汉字的城市名称，可带市后缀")
        return value


class City(BaseModel):
    name: str
    country: Literal["CN"] = "CN"
    seed_available: bool
    identity_verified: bool = False


class Place(BaseModel):
    name: str
    kind: Literal["residential", "employment", "hub", "landmark", "education"]
    placeholder: bool = False


class Scenario(BaseModel):
    kind: Literal["home_to_work", "hub_to_work", "hub_to_landmark", "home_to_education", "home_to_services"]
    persona: str
    purpose: str
    possible_difficulties: list[str]
    difficulties_verified: bool = False


class Candidate(BaseModel):
    id: str
    origin: Place
    destination: Place
    scenario: Scenario
    landmark_relevance: float = Field(ge=0, le=1)
    scenario_relevance: float = Field(ge=0, le=1)
    friction_relevance: float = Field(ge=0, le=1)


class Monologue(BaseModel):
    sentences: list[str]
    text: str
    provider: Literal["mock", "openai_compatible"]
    simulated: bool = True
    format_validated: bool = True


class CommuteRoute(BaseModel):
    id: str
    origin: Place
    destination: Place
    scenario: Scenario
    score: float
    score_components: dict[str, float]
    monologue: Monologue
    data_source: Literal["mock_seed", "mock_generic"]
    route_verified: bool = False
    geometry: None = None
    transport_hint: str = "公共交通场景假设；未核验线路与换乘"


class CommuteResponse(BaseModel):
    city: City
    routes: list[CommuteRoute]
    narrative_options: NarrativeOptions
    warnings: list[str]
