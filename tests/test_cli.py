import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from city_commute.cli import main
from city_commute.config import Settings
from city_commute.llm import chinese_length


@pytest.fixture
def settings():
    return Settings(_env_file=None, data_provider="mock", llm_provider="mock")


@pytest.mark.parametrize("city", ["北京", "上海", "广州", "深圳"])
def test_seed_end_to_end(city, settings, tmp_path, capsys):
    path = tmp_path / "result.json"
    assert main(["--city", city, "--output", str(path)], settings=settings) == 0
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert city in raw
    assert len(data["routes"]) == 4
    assert data["city"]["seed_available"]
    assert len({r["scenario"]["kind"] for r in data["routes"]}) == 4
    assert data["display_text"] in capsys.readouterr().out
    assert "可能难点（未核验）" in data["display_text"]
    for route in data["routes"]:
        assert route["data_source"] == "mock_seed"
        assert not route["route_verified"]
        assert not route["scenario"]["difficulties_verified"]
        assert route["geometry"] is None
        narrative = route["monologue"]
        assert narrative["simulated"] and narrative["provider"] == "mock"
        assert len(narrative["sentences"]) == 6
        assert all(20 <= chinese_length(s) <= 30 and "我" in s for s in narrative["sentences"])
        assert narrative["text"] == "".join(narrative["sentences"])


def test_unknown_city_and_custom_format(settings, tmp_path):
    path = tmp_path / "nested" / "杭州.json"
    assert main(["--city", " 杭州市 ", "--routes", "5", "--sentences", "5",
                 "--min-chars", "25", "--max-chars", "35", "--output", str(path)], settings=settings) == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["city"]["name"] == "杭州"
    assert not data["city"]["seed_available"]
    assert len(data["routes"]) == 5
    for route in data["routes"]:
        assert route["origin"]["placeholder"] and route["destination"]["placeholder"]
        assert route["data_source"] == "mock_generic"
        assert len(route["monologue"]["sentences"]) == 5
        assert all(25 <= chinese_length(s) <= 35 for s in route["monologue"]["sentences"])


@pytest.mark.parametrize("args", [
    ["--city", " "], ["--city", "Beijing"], ["--city", "北京", "--routes", "2"],
    ["--city", "北京", "--routes", "6"], ["--city", "北京", "--min-chars", "35", "--max-chars", "20"],
    ["--city", "北京", "--sentences", "0"],
])
def test_invalid_requests(settings, tmp_path, args, capsys):
    path = tmp_path / "invalid.json"
    assert main(args + ["--output", str(path)], settings=settings) == 2
    assert capsys.readouterr().err
    assert not path.exists()


def test_partial_override_and_default_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None, route_count=3, sentence_count=5, min_chars=18, max_chars=28,
                        llm_provider="mock", data_provider="mock", output_dir=Path("results"))
    assert main(["--city", "北京", "--sentences", "4"], settings=settings) == 0
    paths = list((tmp_path / "results").glob("北京_*.json"))
    assert len(paths) == 1
    data = json.loads(paths[0].read_text(encoding="utf-8"))
    assert len(data["routes"]) == 3
    assert data["narrative_options"] == {"sentence_count": 4, "min_chars": 18, "max_chars": 28}


def test_real_data_not_silently_mocked(settings, tmp_path, capsys):
    path = tmp_path / "real.json"
    assert main(["--city", "北京", "--data-provider", "osm_wikidata", "--output", str(path)], settings=settings) == 1
    assert "尚未实现" in capsys.readouterr().err
    assert not path.exists()


def test_existing_output_is_preserved(settings, tmp_path):
    path = tmp_path / "previous.json"
    path.write_text("previous content", encoding="utf-8")
    assert main(["--city", "北京", "--output", str(path)], settings=settings) == 1
    assert path.read_text(encoding="utf-8") == "previous content"


def test_output_error(settings, tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    assert main(["--city", "北京", "--output", str(blocker / "result.json")], settings=settings) == 1
    assert "执行失败" in capsys.readouterr().err


def test_module_entrypoint(tmp_path):
    env = {key: value for key, value in os.environ.items() if not key.startswith("COMMUTE_")}
    env.update(COMMUTE_DATA_PROVIDER="mock", COMMUTE_LLM_PROVIDER="mock", PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    path = tmp_path / "entrypoint.json"
    result = subprocess.run([sys.executable, "-m", "city_commute", "--city", "北京", "--output", str(path)],
                            cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode == 0, result.stderr
    assert "JSON 已保存" in result.stdout
    assert len(json.loads(path.read_text(encoding="utf-8"))["routes"]) == 4
    bad = subprocess.run([sys.executable, "-m", "city_commute", "--city", "北京", "--routes", "2"],
                         cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert bad.returncode == 2 and "参数或配置错误" in bad.stderr


def test_help_and_missing_city(capsys):
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == 0
    assert "--output" in capsys.readouterr().out
    with pytest.raises(SystemExit) as missing:
        main([])
    assert missing.value.code == 2
