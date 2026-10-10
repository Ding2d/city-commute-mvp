import pytest

from city_commute.config import Settings
from city_commute.providers.mock import MockDataProvider
from city_commute.scoring import rank, score


def test_weighted_score_and_diversity():
    _, candidates = MockDataProvider().candidates("北京")
    settings = Settings(_env_file=None, llm_provider="mock")
    value, components = score(candidates[0], settings)
    assert value == pytest.approx(0.79)
    assert sum(components.values()) == pytest.approx(value)
    selected = rank(candidates, 4, settings)
    assert len({c.scenario.kind for c in selected}) == 4
    assert rank(candidates, 5, settings) == rank(candidates, 5, settings)
    assert len({c.id for c in rank(candidates, 5, settings)}) == 5


def test_bad_config():
    with pytest.raises(ValueError):
        Settings(_env_file=None, min_chars=31, max_chars=20)
    with pytest.raises(ValueError):
        Settings(_env_file=None, score_landmark_weight=0, score_scenario_weight=0, score_friction_weight=0)
    with pytest.raises(ValueError):
        Settings(_env_file=None, llm_provider="openai_compatible", llm_api_key="", llm_model="")
