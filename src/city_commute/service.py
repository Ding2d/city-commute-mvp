from city_commute.config import Settings
from city_commute.llm import NarrativeProvider
from city_commute.models import CommuteRequest, CommuteResponse, CommuteRoute, NarrativeOptions
from city_commute.providers.base import DataProvider
from city_commute.scoring import rank, score


class CommuteService:
    def __init__(self, settings: Settings, data: DataProvider, narrator: NarrativeProvider):
        self.settings, self.data, self.narrator = settings, data, narrator

    async def generate(self, request: CommuteRequest) -> CommuteResponse:
        city, candidates = self.data.candidates(request.city)
        options = request.narrative or NarrativeOptions(
            sentence_count=self.settings.sentence_count,
            min_chars=self.settings.min_chars, max_chars=self.settings.max_chars,
        )
        count = request.route_count or self.settings.route_count
        selected = rank(candidates, count, self.settings)
        if len(selected) < count:
            raise ValueError("候选路线不足，无法满足请求数量")
        routes = []
        for candidate in selected:
            value, components = score(candidate, self.settings)
            routes.append(CommuteRoute(
                id=candidate.id, origin=candidate.origin, destination=candidate.destination,
                scenario=candidate.scenario, score=value, score_components=components,
                monologue=await self.narrator.generate(candidate, options),
                data_source="mock_seed" if city.seed_available else "mock_generic",
            ))
        warnings = [
            "第一阶段全部路线为模拟场景，未核验地理连通性、公共交通线路、换乘与时长。",
            "人物、目的、难点及规则评分为人工场景假设，不代表真实通勤统计或热门程度。",
            "地标游览属于广义城市出行情景，并非严格日常通勤。",
        ]
        if not city.seed_available:
            warnings.append("城市名称未核验；该城市无种子库，使用通用占位地点，不能证明当地真实存在。")
        if self.settings.llm_provider == "mock":
            warnings.append("独白使用离线模板；自定义较窄字数范围时可能截断句意。")
        return CommuteResponse(city=city, routes=routes, narrative_options=options, warnings=warnings)
