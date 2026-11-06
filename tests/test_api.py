import json

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import AsyncOpenAI

from product_cards.api import app

PRODUCT = {
    "name": "Манометр",
    "manufacturer": "Testo",
    "specs": {"Диапазон": "0–100 гПа"},
    "description": "Измеряет дифференциальное давление.",
}
SENTENCE = "Прибор предназначен для измерения дифференциального давления. "
DRAFT = {
    "seo_title": "Дифференциальный манометр Testo",
    "seo_description": SENTENCE * 15,
    "search_queries": ["манометр Testo", "дифференциальный манометр", "измерение давления"],
    "commercial_block": "Для измерения дифференциального давления.",
    "evidence": [
        {
            "block": "seo_description",
            "claim": SENTENCE.strip(),
            "source_field": "description",
            "source_quote": "Измеряет дифференциальное давление.",
        }
    ],
}


def provider_response(data=None, *, status="completed", refusal=False):
    content = (
        {"type": "refusal", "refusal": "Отказ"}
        if refusal
        else {
            "type": "output_text",
            "text": json.dumps(data or DRAFT, ensure_ascii=False),
            "annotations": [],
            "logprobs": [],
        }
    )
    return {
        "id": "resp_test",
        "object": "response",
        "created_at": 1,
        "status": status,
        "error": None,
        "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
        "instructions": None,
        "max_output_tokens": 4000,
        "model": "test-model",
        "output": [
            {
                "id": "msg_test",
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [content],
            }
        ],
        "parallel_tool_calls": True,
        "previous_response_id": None,
        "reasoning": {"effort": None, "summary": None},
        "store": False,
        "temperature": 1,
        "text": {"format": {"type": "text"}},
        "tool_choice": "auto",
        "tools": [],
        "top_p": 1,
        "truncation": "disabled",
        "usage": None,
        "metadata": {},
    }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("product_cards.api.load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with TestClient(app) as c:
        yield c


def use_provider(client, handler):
    client.app.state.llm = AsyncOpenAI(
        api_key="test-not-a-secret",
        max_retries=0,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    client.app.state.model = "test-model"


def test_generate_with_real_sdk(client):
    def handler(request):
        body = json.loads(request.content)
        assert body["store"] is False
        assert body["text"]["format"]["strict"] is True
        assert json.loads(body["input"][0]["content"]) == PRODUCT
        return httpx.Response(200, json=provider_response())

    use_provider(client, handler)
    response = client.post("/generate", json=PRODUCT)
    assert response.status_code == 200
    assert response.json()["characteristics"] == {"Диапазон": "0–100 гПа"}
    assert response.json()["status"] == "ok"


def test_repairs_once(client):
    attempts = []

    def handler(request):
        attempts.append(json.loads(request.content))
        data = dict(DRAFT)
        if len(attempts) == 1:
            data["seo_title"] = "x" * 71
        return httpx.Response(200, json=provider_response(data))

    use_provider(client, handler)
    response = client.post("/generate", json=PRODUCT)
    assert response.status_code == 200
    assert len(attempts) == 2
    assert "Исправь" in attempts[1]["input"][-1]["content"]


def test_two_invalid_answers_fail_safely(client):
    attempts = []

    def handler(request):
        attempts.append(1)
        return httpx.Response(200, json=provider_response({**DRAFT, "commercial_block": "999 МПа"}))

    use_provider(client, handler)
    response = client.post("/generate", json=PRODUCT)
    assert response.status_code == 502
    assert len(attempts) == 2
    assert "999" not in response.text


@pytest.mark.parametrize("status,refusal", [("incomplete", False), ("completed", True)])
def test_refusal_or_incomplete(client, status, refusal):
    use_provider(
        client,
        lambda r: httpx.Response(200, json=provider_response(status=status, refusal=refusal)),
    )
    assert client.post("/generate", json=PRODUCT).status_code == 502


@pytest.mark.parametrize("upstream,expected", [(429, 429), (401, 502), (500, 502)])
def test_provider_errors_are_safe(client, upstream, expected):
    use_provider(
        client,
        lambda r: httpx.Response(
            upstream, json={"error": {"message": "SECRET_PROVIDER_DETAIL", "type": "api_error"}}
        ),
    )
    response = client.post("/generate", json=PRODUCT)
    assert response.status_code == expected
    assert "SECRET_PROVIDER_DETAIL" not in response.text
    assert "test-not-a-secret" not in response.text


def test_timeout(client):
    def handler(request):
        raise httpx.ReadTimeout("SECRET_TIMEOUT", request=request)

    use_provider(client, handler)
    response = client.post("/generate", json=PRODUCT)
    assert response.status_code == 504
    assert "SECRET_TIMEOUT" not in response.text


def test_missing_configuration(client):
    assert client.post("/generate", json=PRODUCT).status_code == 503


def test_incomplete_input_needs_no_key(client):
    response = client.post("/generate", json={"name": "Прибор"})
    assert response.status_code == 200
    assert response.json()["status"] == "needs_clarification"


@pytest.mark.parametrize(
    "body", ["{", '{"name": " "}', '{"name": 5}', '{"name":"A","secret":"PRIVATE_INPUT"}']
)
def test_invalid_json_is_safe(client, body):
    response = client.post("/generate", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert "PRIVATE_INPUT" not in response.text


def test_body_limit(client):
    assert client.post("/generate", content=b"x" * 65537).status_code == 413


def test_streamed_body_limit(client):
    def chunks():
        yield b"x" * 40000
        yield b"x" * 40000

    response = client.post("/generate", content=chunks())
    assert response.status_code == 413


def test_mixed_refusal_is_rejected_without_retry(client):
    attempts = []

    def handler(request):
        attempts.append(1)
        response = provider_response()
        response["output"][0]["content"].append({"type": "refusal", "refusal": "Cannot generate"})
        return httpx.Response(200, json=response)

    use_provider(client, handler)
    assert client.post("/generate", json=PRODUCT).status_code == 502
    assert len(attempts) == 1


def test_exhausted_balance_has_actionable_error(client):
    use_provider(
        client,
        lambda r: httpx.Response(
            429,
            json={
                "error": {
                    "message": "PRIVATE_DETAIL",
                    "code": "credit_balance_exhausted",
                    "type": "insufficient_quota",
                }
            },
        ),
    )
    response = client.post("/generate", json=PRODUCT)
    assert response.status_code == 429
    assert "баланс" in response.json()["detail"].lower()
    assert "PRIVATE_DETAIL" not in response.text
