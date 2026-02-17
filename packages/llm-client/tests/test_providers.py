"""Unit tests for provider implementations (no API calls)."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from llm_client import LLMProviderError, LLMResponseError, ModelConfig, Provider


@pytest.fixture
def temp_schema_file(tmp_path):
    """Create a temporary schema file."""
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"case_id": {"type": "string"}},
    }
    schema_file = tmp_path / "case.schema.json"
    schema_file.write_text(json.dumps(schema))
    return schema_file


@pytest.fixture
def openai_config(temp_schema_file):
    """OpenAI configuration with temp schema."""
    return ModelConfig(
        provider=Provider.OPENAI,
        model="gpt-4o",
        api_key="sk-test-key",
        temperature=0.7,
        max_tokens=4096,
        schema_path=str(temp_schema_file),
    )


@pytest.fixture
def anthropic_config(temp_schema_file):
    """Anthropic configuration with temp schema."""
    return ModelConfig(
        provider=Provider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key="sk-ant-test-key",
        temperature=0.7,
        max_tokens=8192,
        schema_path=str(temp_schema_file),
    )


class TestOpenAICaseGenerator:
    """Tests for OpenAICaseGenerator."""

    def test_init_loads_schema(self, openai_config):
        """Test that __init__ loads the schema file."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        with patch("openai.OpenAI"):
            generator = OpenAICaseGenerator(openai_config)
            assert generator.schema_text is not None
            assert len(generator.schema_text) > 0
            assert "case_id" in generator.schema_text

    def test_init_missing_schema_path(self):
        """Test that missing schema_path raises error."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        config = ModelConfig(provider=Provider.OPENAI, model="gpt-4o", api_key="test")

        with pytest.raises(ValueError, match="schema_path required"):
            OpenAICaseGenerator(config)

    def test_init_nonexistent_schema_file(self):
        """Test that nonexistent schema file raises error."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            api_key="test",
            schema_path="/nonexistent/schema.json",
        )

        with patch("openai.OpenAI"):
            with pytest.raises(LLMProviderError, match="Schema file not found"):
                OpenAICaseGenerator(config)

    def test_init_without_openai_package(self, openai_config):
        """Test that missing openai package gives helpful error."""
        from llm_client.openai_generator import OpenAICaseGenerator

        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(LLMProviderError, match="openai package not installed"):
                OpenAICaseGenerator(openai_config)

    def test_generate_case_calls_api(self, openai_config, sample_case_seed):
        """Test that generate_case calls OpenAI API."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"case_id": "test-123"}'))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("openai.OpenAI", return_value=mock_client):
            generator = OpenAICaseGenerator(openai_config)
            result = generator.generate_case(sample_case_seed)

            # Verify API was called
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]

            assert call_kwargs["model"] == "gpt-4o"
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["max_tokens"] == 4096
            assert call_kwargs["response_format"] == {"type": "json_object"}

            # Verify result
            assert isinstance(result, dict)
            assert result["case_id"] == "test-123"

    def test_generate_case_empty_content(self, openai_config, sample_case_seed):
        """Test handling of empty content from API."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("openai.OpenAI", return_value=mock_client):
            generator = OpenAICaseGenerator(openai_config)

            with pytest.raises(LLMResponseError, match="empty content"):
                generator.generate_case(sample_case_seed)

    def test_generate_case_invalid_json(self, openai_config, sample_case_seed):
        """Test handling of invalid JSON from API."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="not valid json {"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("openai.OpenAI", return_value=mock_client):
            generator = OpenAICaseGenerator(openai_config)

            with pytest.raises(LLMResponseError, match="Failed to parse JSON"):
                generator.generate_case(sample_case_seed)

    def test_generate_case_api_error(self, openai_config, sample_case_seed):
        """Test handling of API errors."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")

        with patch("openai.OpenAI", return_value=mock_client):
            generator = OpenAICaseGenerator(openai_config)

            with pytest.raises(LLMProviderError, match="OpenAI API call failed"):
                generator.generate_case(sample_case_seed)

    def test_build_system_prompt_includes_schema(self, openai_config):
        """Test that system prompt includes schema text."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        with patch("openai.OpenAI"):
            generator = OpenAICaseGenerator(openai_config)
            system_prompt = generator._build_system_prompt()

            assert "case_id" in system_prompt
            assert "schema" in system_prompt.lower()
            assert "json" in system_prompt.lower()

    def test_build_user_prompt_includes_seed_fields(self, openai_config, sample_case_seed):
        """Test that user prompt includes seed information."""
        pytest.importorskip("openai")
        from llm_client.openai_generator import OpenAICaseGenerator

        with patch("openai.OpenAI"):
            generator = OpenAICaseGenerator(openai_config)
            user_prompt = generator._build_user_prompt(sample_case_seed)

            assert sample_case_seed.diagnosis in user_prompt
            assert sample_case_seed.difficulty in user_prompt
            assert sample_case_seed.dramatic_tone in user_prompt


class TestAnthropicCaseGenerator:
    """Tests for AnthropicCaseGenerator."""

    def test_init_loads_schema(self, anthropic_config):
        """Test that __init__ loads the schema file."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        with patch("anthropic.Anthropic"):
            generator = AnthropicCaseGenerator(anthropic_config)
            assert generator.schema_text is not None
            assert len(generator.schema_text) > 0
            assert "case_id" in generator.schema_text

    def test_init_missing_schema_path(self):
        """Test that missing schema_path raises error."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        config = ModelConfig(
            provider=Provider.ANTHROPIC, model="claude-sonnet-4-20250514", api_key="test"
        )

        with pytest.raises(ValueError, match="schema_path required"):
            AnthropicCaseGenerator(config)

    def test_init_nonexistent_schema_file(self):
        """Test that nonexistent schema file raises error."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-sonnet-4-20250514",
            api_key="test",
            schema_path="/nonexistent/schema.json",
        )

        with patch("anthropic.Anthropic"):
            with pytest.raises(LLMProviderError, match="Schema file not found"):
                AnthropicCaseGenerator(config)

    def test_init_without_anthropic_package(self, anthropic_config):
        """Test that missing anthropic package gives helpful error."""
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(LLMProviderError, match="anthropic package not installed"):
                AnthropicCaseGenerator(anthropic_config)

    def test_generate_case_calls_api(self, anthropic_config, sample_case_seed):
        """Test that generate_case calls Anthropic API."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        # Mock the Anthropic client
        mock_client = MagicMock()
        mock_text_block = Mock(text='{"case_id": "test-456"}')
        mock_response = Mock(content=[mock_text_block])
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            generator = AnthropicCaseGenerator(anthropic_config)
            result = generator.generate_case(sample_case_seed)

            # Verify API was called
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]

            assert call_kwargs["model"] == "claude-sonnet-4-20250514"
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["max_tokens"] == 8192

            # Verify result
            assert isinstance(result, dict)
            assert result["case_id"] == "test-456"

    def test_generate_case_empty_content(self, anthropic_config, sample_case_seed):
        """Test handling of empty content from API."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        mock_client = MagicMock()
        mock_response = Mock(content=[])
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            generator = AnthropicCaseGenerator(anthropic_config)

            with pytest.raises(LLMResponseError, match="empty content"):
                generator.generate_case(sample_case_seed)

    def test_generate_case_invalid_json(self, anthropic_config, sample_case_seed):
        """Test handling of invalid JSON from API."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        mock_client = MagicMock()
        mock_text_block = Mock(text="invalid json [[[")
        mock_response = Mock(content=[mock_text_block])
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            generator = AnthropicCaseGenerator(anthropic_config)

            with pytest.raises(LLMResponseError, match="Failed to parse JSON"):
                generator.generate_case(sample_case_seed)

    def test_generate_case_api_error(self, anthropic_config, sample_case_seed):
        """Test handling of API errors."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")

        with patch("anthropic.Anthropic", return_value=mock_client):
            generator = AnthropicCaseGenerator(anthropic_config)

            with pytest.raises(LLMProviderError, match="Anthropic API call failed"):
                generator.generate_case(sample_case_seed)

    def test_build_system_prompt_includes_schema(self, anthropic_config):
        """Test that system prompt includes schema text."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        with patch("anthropic.Anthropic"):
            generator = AnthropicCaseGenerator(anthropic_config)
            system_prompt = generator._build_system_prompt()

            assert "case_id" in system_prompt
            assert "schema" in system_prompt.lower()
            assert "json" in system_prompt.lower()

    def test_build_user_prompt_includes_seed_fields(self, anthropic_config, sample_case_seed):
        """Test that user prompt includes seed information."""
        pytest.importorskip("anthropic")
        from llm_client.anthropic_generator import AnthropicCaseGenerator

        with patch("anthropic.Anthropic"):
            generator = AnthropicCaseGenerator(anthropic_config)
            user_prompt = generator._build_user_prompt(sample_case_seed)

            assert sample_case_seed.diagnosis in user_prompt
            assert sample_case_seed.difficulty in user_prompt
            assert sample_case_seed.dramatic_tone in user_prompt
