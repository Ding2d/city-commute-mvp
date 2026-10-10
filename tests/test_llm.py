import asyncio
import json

import httpx
import pytest

from city_commute.cli import main
from city_commute.config import Settings
from city_commute.llm import MockNarrativeProvider, NarrativeError, OpenAICompatibleNarrativeProvider
from city_commute.models import NarrativeOptions
from city_commute.providers.mock import MockDataProvider
from city_commute.service import CommuteService


def make_settings(**kwargs):
    return Settings(_env_file=None, llm_provider="openai_compatible", llm_api_key="test-only", llm_model="test", **kwargs)


def test_compatible_request_and_retry():
    candidate = MockDataProvider().candidates("北京")[1][0]
    options = NarrativeOptions()
    valid = asyncio.run(MockNarrativeProvider().generate(candidate, options)).sentences
    calls = []

    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert body["model"] == "test"
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-only"
        content = '{"sentences":[]}' if len(calls) == 1 else json.dumps({"sentences": valid})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    provider = OpenAICompatibleNarrativeProvider(make_settings(), httpx.MockTransport(handler))
    result = asyncio.run(provider.generate(candidate, options))
    assert result.provider == "openai_compatible" and result.sentences == valid
    assert len(calls) == 2


@pytest.mark.parametrize("mode", ["http_error", "timeout", "invalid_json", "malformed_envelope"])
def test_llm_failure_returns_nonzero_without_secret(mode, tmp_path, capsys):
    def handler(request):
        if mode == "http_error":
            return httpx.Response(401, text="test-only secret")
        if mode == "timeout":
            raise httpx.ReadTimeout("test-only secret", request=request)
        if mode == "malformed_envelope":
            return httpx.Response(200, json={"choices": []})
        return httpx.Response(200, json={"choices": [{"message": {"content": "bad"}}]})

    settings = make_settings(llm_format_retries=0)
    data = MockDataProvider()
    service = CommuteService(settings, data, OpenAICompatibleNarrativeProvider(settings, httpx.MockTransport(handler)))
    path = tmp_path / "failed.json"
    assert main(["--city", "北京", "--output", str(path)], settings=settings, service=service) == 1
    output = capsys.readouterr()
    assert "执行失败" in output.err
    assert "test-only" not in output.err
    assert not path.exists()


def test_format_validation():
    from city_commute.llm import validate_sentences

    with pytest.raises(NarrativeError):
        validate_sentences(["他今天准备出门。"] * 6, NarrativeOptions())
    with pytest.raises(NarrativeError):
        validate_sentences(["我出门。我要上班。"] * 6, NarrativeOptions())
