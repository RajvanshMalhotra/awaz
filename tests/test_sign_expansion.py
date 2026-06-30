import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_generate_sign_expansion_streams_tokens():
    from llm.service import LLMService

    mock_stream = AsyncMock()
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content='{"expressive_text": "Haan yaar"}'))]

    async def _fake_stream():
        yield mock_chunk

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_fake_stream())

    svc = LLMService.__new__(LLMService)
    svc._client = mock_client
    svc._model = "test-model"
    svc._system_prompt = "test prompt"

    tokens = []
    async for token in svc.generate_sign_expansion(
        signed_words=["food"],
        context=["Are you hungry?"],
        accepted_phrases=["Haan yaar, kuch khaana chahiye"],
    ):
        tokens.append(token)
    assert len(tokens) > 0

def test_build_sign_prompt_includes_words_and_context():
    from llm.service import LLMService
    svc = LLMService.__new__(LLMService)
    svc._profile_name = "Raj"
    prompt = svc._build_sign_prompt(
        signed_words=["food", "want"],
        context=["Are you hungry?", "Do you want chai?"],
        accepted_phrases=["Haan yaar, kuch khaana chahiye"],
    )
    assert "food" in prompt
    assert "want" in prompt
    assert "Are you hungry?" in prompt
    assert "Haan yaar" in prompt
