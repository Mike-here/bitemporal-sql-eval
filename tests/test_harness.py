import json

import httpx
import pytest

from harness.providers import ProviderError, generate, output_text, request_payload
from harness.replay import replay
from harness.run import run_trial
from harness.tasks import ROOT, load_task


def model():
    return json.loads((ROOT / "configs/models.json").read_text())["models"][0]


def response(sql, status="completed"):
    return {"id": "mock-not-a-real-run", "model": "mock-model-not-empirical", "status": status,
            "output": [{"type": "message", "content": [{"type": "output_text", "text": sql}]}],
            "usage": {"input_tokens": 100, "output_tokens": 100}}


def test_request_contains_only_public_prompt_and_schema(task):
    payload = request_payload(model(), task.model_input)
    assert payload["input"] == task.model_input
    assert task.schema in payload["input"]
    assert "seed_4300" not in json.dumps(payload)
    assert "reference/t01" not in json.dumps(payload)
    assert "expected" not in payload  # There is no grading feedback channel.
    assert "temperature" not in payload
    assert payload["tools"] == []
    assert "previous_response_id" not in payload


def test_mocked_provider_contract(task, reference_sql):
    def handle(request):
        assert request.url.path == "/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-key-not-real"
        assert json.loads(request.content)["store"] is False
        return httpx.Response(200, json=response(reference_sql))
    payload, received = generate(model(), task.model_input, "test-key-not-real", transport=httpx.MockTransport(handle))
    assert output_text(received) == reference_sql
    assert "test-key-not-real" not in json.dumps(payload)


def test_mocked_http_failure_is_sanitized(task):
    def handle(request):
        return httpx.Response(401, json={"error": "test-key-must-not-leak"}, headers={"x-request-id": "mock-request"})
    with pytest.raises(ProviderError) as caught:
        generate(model(), task.model_input, "test-key-must-not-leak", transport=httpx.MockTransport(handle))
    assert "401" in str(caught.value)
    assert "test-key-must-not-leak" not in str(caught.value)


def test_completed_mock_trial_and_exact_offline_replay(task, reference_sql):
    def fake_generate(selected, prompt, key):
        return request_payload(selected, prompt), response(reference_sql)
    record = run_trial(task, model(), "fake-key", 1, generate_fn=fake_generate)
    assert record["status"] == "graded"
    assert record["grade"]["passed"]
    loaded = json.loads(json.dumps(record))
    assert replay(loaded)["replay_matches"]
    assert "fake-key" not in json.dumps(record)
    loaded["artifact_hashes"] = {}
    with pytest.raises(ValueError, match="hashes"):
        replay(loaded)


def test_replay_rejects_runtime_change(task, reference_sql):
    def fake_generate(selected, prompt, key):
        return request_payload(selected, prompt), response(reference_sql)
    record = json.loads(json.dumps(run_trial(task, model(), "fake-key", 1, generate_fn=fake_generate)))
    record["environment"]["sqlite"] = "0.0.0"
    with pytest.raises(ValueError, match="runtime"):
        replay(record)


@pytest.mark.parametrize("status", ["incomplete", "failed", "queued"])
def test_incomplete_and_failed_responses_are_not_scored_as_semantic_failures(task, reference_sql, status):
    def fake_generate(selected, prompt, key):
        return request_payload(selected, prompt), response(reference_sql, status)
    record = run_trial(task, model(), "fake-key", 1, generate_fn=fake_generate)
    assert "grade" not in record
    assert record["status"] == ("incomplete" if status == "incomplete" else "api_error")


def test_api_failure_recorded_without_retry(task):
    calls = []
    def fail(*args):
        calls.append(1)
        raise ProviderError("HTTP 429")
    record = run_trial(task, model(), "fake-key", 1, generate_fn=fail)
    assert calls == [1]
    assert record["status"] == "api_error"
    assert "grade" not in record


def test_unimplemented_task_rejected_before_api_access():
    with pytest.raises(ValueError, match="not implemented"):
        load_task("t99")


def test_native_gemini_request_and_visible_sql_only(task, reference_sql):
    selected = {"provider": "gemini", "model": "test-pro", "max_output_tokens": 8192,
                "thinking_config": {"thinkingLevel": "HIGH"}}
    def handle(request):
        assert request.url.path.endswith("/models/test-pro:generateContent")
        assert request.headers["x-goog-api-key"] == "fake-google-key"
        assert "key=" not in str(request.url)
        payload = json.loads(request.content)
        assert payload["contents"][0]["parts"][0]["text"] == task.model_input
        return httpx.Response(200, json={"modelVersion": "test-pro", "candidates": [
            {"finishReason": "STOP", "content": {"parts": [{"thought": True, "text": "hidden thought"}, {"text": reference_sql}]}}]})
    _, received = generate(selected, task.model_input, "fake-google-key", transport=httpx.MockTransport(handle))
    assert output_text(received) == reference_sql
