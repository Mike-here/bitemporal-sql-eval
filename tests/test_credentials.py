from harness.credentials import load_credentials


def test_env_parser_preserves_keys_and_never_executes_substitutions(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    path = tmp_path / ".env"
    path.write_text('export OPENAI_API_KEY="fake-value" # comment\nGEMINI_API_KEY=\'$(touch forbidden)\'\nIGNORED_SECRET=ignored\n')
    assert load_credentials(path) == {"OPENAI_API_KEY": "fake-value", "GEMINI_API_KEY": "$(touch forbidden)"}
    assert not (tmp_path / "forbidden").exists()
