from city_commute.config import Settings
from city_commute.models import Candidate


def score(candidate: Candidate, settings: Settings) -> tuple[float, dict[str, float]]:
    weights = {
        "landmark": settings.score_landmark_weight,
        "scenario": settings.score_scenario_weight,
        "friction": settings.score_friction_weight,
    }
    features = {"landmark": candidate.landmark_relevance, "scenario": candidate.scenario_relevance,
                "friction": candidate.friction_relevance}
    total = sum(weights.values())
    components = {key: weights[key] * features[key] / total for key in weights}
    return round(sum(components.values()), 4), components


def rank(candidates: list[Candidate], count: int, settings: Settings) -> list[Candidate]:
    # First cover distinct scenario kinds, then fill remaining slots by score.
    ordered = sorted(candidates, key=lambda item: (-score(item, settings)[0], item.id))
    selected, seen = [], set()
    for item in ordered:
        if item.scenario.kind not in seen:
            selected.append(item)
            seen.add(item.scenario.kind)
        if len(selected) == count:
            return sorted(selected, key=lambda item: -score(item, settings)[0])
    selected_ids = {item.id for item in selected}
    selected.extend(item for item in ordered if item.id not in selected_ids)
    return sorted(selected[:count], key=lambda item: -score(item, settings)[0])
