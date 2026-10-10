"""Readable presentation and UTF-8 JSON export, independent of generation."""
import json
from pathlib import Path

from city_commute.models import CommuteResponse


def render_text(result: CommuteResponse) -> str:
    lines = [f"{result.city.name} · 模拟通勤场景（{len(result.routes)}条）", ""]
    for warning in result.warnings:
        lines.append(f"说明：{warning}")
    for index, route in enumerate(result.routes, 1):
        lines.extend([
            "", f"路线 {index}：{route.origin.name} → {route.destination.name}",
            f"模拟人物：{route.scenario.persona}", f"出行目的：{route.scenario.purpose}",
            "可能难点（未核验）：" + "、".join(route.scenario.possible_difficulties),
            f"规则评分：{route.score:.3f}（场景假设，不代表真实热门程度）",
            f"数据来源：{route.data_source}；独白来源：{route.monologue.provider}",
            "内心独白（模拟）：", *route.monologue.sentences,
        ])
    return "\n".join(lines)


def save_json(result: CommuteResponse, text: str, path: Path) -> None:
    payload = result.model_dump(mode="json")
    payload["display_text"] = text
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        try:
            stream.write(serialized)
        except OSError:
            stream.close()
            path.unlink(missing_ok=True)
            raise
