import json
from importlib.resources import files

from city_commute.models import Candidate, City, Place, Scenario


# Rule templates describe hypothetical groups and friction, not empirical findings.
TEMPLATES = [
    ("home_to_work", "residential", "employment", "企业职员", "到单位上班", ["高峰候车拥挤", "换乘步行较长"]),
    ("home_to_work", "residential", "employment", "园区工作人员", "到园区上班", ["末段接驳等待", "早高峰道路拥堵"]),
    ("hub_to_work", "hub", "employment", "出差工作者", "前往商务会面", ["携带行李换乘", "陌生出口辨认"]),
    ("hub_to_landmark", "hub", "landmark", "外地访客", "前往地标游览", ["陌生出口辨认", "步行寻找入口"]),
    ("home_to_education", "residential", "education", "高校学生", "赶往校园上课", ["候车时间不定", "校门附近步行"]),
]


class MockDataProvider:
    def __init__(self):
        self.seeds = json.loads(files("city_commute").joinpath("data/seeds.json").read_text(encoding="utf-8"))

    def candidates(self, city_name: str) -> tuple[City, list[Candidate]]:
        known = city_name in self.seeds
        pairs = self.seeds.get(city_name, [
            ["住宅片区甲（占位）", "就业中心甲（占位）"],
            ["住宅片区乙（占位）", "产业园区（占位）"],
            ["交通枢纽甲（占位）", "商务中心（占位）"],
            ["交通枢纽乙（占位）", "城市地标（占位）"],
            ["住宅片区丙（占位）", "高校片区（占位）"],
        ])
        candidates = []
        for i, (pair, template) in enumerate(zip(pairs, TEMPLATES)):
            kind, origin_kind, destination_kind, persona, purpose, friction = template
            candidates.append(Candidate(
                id=f"{city_name}-mock-{i + 1}",
                origin=Place(name=pair[0], kind=origin_kind, placeholder=not known),
                destination=Place(name=pair[1], kind=destination_kind, placeholder=not known),
                scenario=Scenario(kind=kind, persona=persona, purpose=purpose, possible_difficulties=friction),
                landmark_relevance=0.8 if known else 0.2,
                scenario_relevance=0.9 if kind == "home_to_work" else 0.7,
                friction_relevance=0.6,
            ))
        return City(name=city_name, seed_available=known), candidates
