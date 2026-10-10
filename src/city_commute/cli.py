import argparse
import asyncio
from datetime import datetime
from pathlib import Path
import sys

from pydantic import ValidationError
from pydantic_settings import SettingsError

from city_commute.config import Settings
from city_commute.llm import MockNarrativeProvider, NarrativeError, OpenAICompatibleNarrativeProvider
from city_commute.models import CommuteRequest, NarrativeOptions
from city_commute.output import render_text, save_json
from city_commute.providers.mock import MockDataProvider
from city_commute.providers.real import OSMWikidataProvider
from city_commute.service import CommuteService


def build_service(settings: Settings) -> CommuteService:
    data = MockDataProvider() if settings.data_provider == "mock" else OSMWikidataProvider()
    narrator = (MockNarrativeProvider() if settings.llm_provider == "mock"
                else OpenAICompatibleNarrativeProvider(settings))
    return CommuteService(settings, data, narrator)


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="生成模拟通勤场景，展示易读文本并保存 UTF-8 JSON。")
    command.add_argument("--city", required=True, help="城市中文名称，例如北京或北京市")
    command.add_argument("--routes", type=int, help="路线数（3–5），默认读取配置")
    command.add_argument("--sentences", type=int, help="每段独白句数（1–12）")
    command.add_argument("--min-chars", type=int, help="每句最少汉字数（10–80）")
    command.add_argument("--max-chars", type=int, help="每句最多汉字数（10–80）")
    command.add_argument("--data-provider", choices=["mock", "osm_wikidata"], help="数据来源；真实来源尚未实现")
    command.add_argument("--llm-provider", choices=["mock", "openai_compatible"], help="独白来源；密钥从环境读取")
    command.add_argument("--output", type=Path, help="JSON 文件路径；默认 outputs/城市_时间戳.json，不覆盖已有文件")
    return command


def main(argv: list[str] | None = None, *, settings: Settings | None = None,
         service: CommuteService | None = None) -> int:
    # Make redirected Chinese output consistent on Windows and Unix.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        overrides = {name: getattr(args, name) for name in ("data_provider", "llm_provider")
                     if getattr(args, name) is not None}
        if settings is None:
            settings = Settings(**overrides)
        elif overrides:
            settings = Settings(_env_file=None, **(settings.model_dump() | overrides))
        options = NarrativeOptions(
            sentence_count=args.sentences if args.sentences is not None else settings.sentence_count,
            min_chars=args.min_chars if args.min_chars is not None else settings.min_chars,
            max_chars=args.max_chars if args.max_chars is not None else settings.max_chars,
        )
        request = CommuteRequest(city=args.city, route_count=args.routes, narrative=options)
        path = args.output or settings.output_dir / f"{request.city}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        if path.suffix.lower() != ".json":
            raise ValueError("输出文件必须使用 .json 扩展名")
        if path.exists():
            raise FileExistsError("输出文件已存在，请指定新路径")
        result = asyncio.run((service or build_service(settings)).generate(request))
        text = render_text(result)
        save_json(result, text, path)
        print(text)
        print(f"\nJSON 已保存：{path.resolve()}")
        return 0
    except ValidationError as exc:
        details = "; ".join(f"{'.'.join(map(str, error['loc'])) or '配置'}: {error['msg']}"
                            for error in exc.errors(include_input=False))
        print(f"参数或配置错误：{details}", file=sys.stderr)
        return 2
    except SettingsError:
        print("配置错误：环境变量无法解析，请检查 .env 和进程环境。", file=sys.stderr)
        return 2
    except (NotImplementedError, NarrativeError, ValueError, OSError) as exc:
        print(f"执行失败：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("执行已取消。", file=sys.stderr)
        return 130
