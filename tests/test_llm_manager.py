"""Test suite for src/llm/llm_manager.py"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langchain_core.prompt_values import StringPromptValue

from src.llm.llm_manager import (
    AIAdapter,
    ClaudeModel,
    GeminiModel,
    GPTAnswerer,
    LLMLogger,
    LoggerChatModel,
    OllamaModel,
    OpenAIModel,
)


@pytest.fixture
def mock_api_key():
    """Provide mock API key"""
    return "test-api-key-12345"


@pytest.fixture
def mock_llm_proxy():
    """Provide mock LLM proxy"""
    return "http://proxy.example.com:8080"


@pytest.fixture
def mock_resume_structured():
    """Provide mock structured resume"""
    return {
        "personal_information": {
            "first_name": "John",
            "last_name": "Doe",
            "gender": "male",
            "email": "john@example.com",
            "phone": "+1234567890",
            "phone_code": "+1",
        },
        "education_details": [
            {
                "education_level": "Bachelor's",
                "institution": "Test University",
                "field_of_study": "Computer Science",
            }
        ],
        "experience_details": [
            {
                "position": "Software Engineer",
                "company": "Tech Corp",
                "employment_period": "2020-2023",
                "key_responsibilities": ["Developed features", "Fixed bugs"],
            }
        ],
        "skills": ["Python", "JavaScript", "AWS"],
        "languages": [{"language": "English", "proficiency": "Native"}],
        "interests": ["Open Source", "Machine Learning"],
        "projects": [],
        "achievements": [],
        "certifications": [],
        "about_me": "Passionate software engineer",
    }


@pytest.fixture
def mock_resume_readable():
    """Provide mock readable resume"""
    return """
John Doe
Software Engineer
Email: john@example.com
Phone: +1234567890

Education:
- Bachelor's in Computer Science, Test University

Experience:
- Software Engineer at Tech Corp (2020-2023)
  * Developed features
  * Fixed bugs

Skills: Python, JavaScript, AWS
Languages: English (Native)
"""


@pytest.fixture
def mock_job():
    """Provide mock job data"""
    return {
        "title": "Senior Python Developer",
        "company_name": "Example Corp",
        "location": "Remote",
        "description": "Looking for experienced Python developer",
        "requirements": ["5+ years Python", "AWS experience"],
    }


class TestGeminiModel:
    """Tests for GeminiModel class"""

    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    def test_gemini_model_initialization(self, mock_chat_gemini, mock_api_key, mock_llm_proxy):
        """Test GeminiModel initialization"""
        model = GeminiModel(mock_api_key, "gemini-pro", mock_llm_proxy)

        assert model.google_api_key == mock_api_key
        mock_chat_gemini.assert_called_once()

    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    def test_gemini_model_invoke(self, mock_chat_gemini, mock_api_key, mock_llm_proxy):
        """Test GeminiModel invoke method"""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_chat_gemini.return_value = mock_model

        model = GeminiModel(mock_api_key, "gemini-pro", mock_llm_proxy)
        mock_prompt = MagicMock()
        mock_prompt.messages = [MagicMock(content="Test prompt")]

        response = model.invoke(mock_prompt)

        assert isinstance(response, AIMessage)
        assert response.content == "Test response"
        mock_model.invoke.assert_called_once()


class TestOpenAIModel:
    """Tests for OpenAIModel class"""

    @patch("langchain_openai.ChatOpenAI")
    def test_openai_model_initialization(self, mock_chat_openai, mock_api_key, mock_llm_proxy):
        """Test OpenAIModel initialization"""
        model = OpenAIModel(mock_api_key, "gpt-4", mock_llm_proxy)

        assert model.openai_api_key == mock_api_key
        assert model.model_name == "gpt-4"
        assert model.llm_proxy == mock_llm_proxy
        mock_chat_openai.assert_called_once()

    @patch("langchain_openai.ChatOpenAI")
    def test_openai_model_invoke_success(self, mock_chat_openai, mock_api_key, mock_llm_proxy):
        """Test OpenAIModel invoke method success"""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_chat_openai.return_value = mock_model

        model = OpenAIModel(mock_api_key, "gpt-4", mock_llm_proxy)
        mock_prompt = MagicMock()
        mock_prompt.messages = [MagicMock(content="Test prompt")]

        response = model.invoke(mock_prompt)

        assert isinstance(response, AIMessage)
        assert response.content == "Test response"


class TestClaudeModel:
    """Tests for ClaudeModel class"""

    @patch("langchain_anthropic.ChatAnthropic")
    def test_claude_model_initialization(self, mock_chat_anthropic, mock_api_key):
        """Test ClaudeModel initialization"""
        _ = ClaudeModel(mock_api_key, "claude-3-opus-20240229")

        mock_chat_anthropic.assert_called_once()

    # @pytest.mark.skipif(True, reason="Requires langchain_anthropic which may not be installed")
    @patch("langchain_anthropic.ChatAnthropic")
    def test_claude_model_invoke(self, mock_chat_anthropic, mock_api_key):
        """Test ClaudeModel invoke method"""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_chat_anthropic.return_value = mock_model

        model = ClaudeModel(mock_api_key, "claude-3-opus-20240229")
        response = model.invoke("Test prompt")

        assert isinstance(response, AIMessage)
        assert response.content == "Test response"


class TestOllamaModel:
    """Tests for OllamaModel class"""

    @patch("langchain_ollama.ChatOllama")
    def test_ollama_model_initialization_with_api_url(self, mock_chat_ollama):
        """Test OllamaModel initialization with API URL"""
        api_url = "http://localhost:11434"
        _ = OllamaModel("llama2", api_url)

        mock_chat_ollama.assert_called_once_with(model="llama2", base_url=api_url)

    @patch("langchain_ollama.ChatOllama")
    def test_ollama_model_initialization_without_api_url(self, mock_chat_ollama):
        """Test OllamaModel initialization without API URL"""
        _ = OllamaModel("llama2", "")

        mock_chat_ollama.assert_called_once_with(model="llama2")

    @patch("langchain_ollama.ChatOllama")
    def test_ollama_model_invoke(self, mock_chat_ollama):
        """Test OllamaModel invoke method"""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_chat_ollama.return_value = mock_model

        model = OllamaModel("llama2", "")
        response = model.invoke("Test prompt")

        assert isinstance(response, AIMessage)
        assert response.content == "Test response"


class TestAIAdapter:
    """Tests for AIAdapter class"""

    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "gemini")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "gemini-pro")
    @patch("src.llm.llm_manager.GeminiModel")
    def test_ai_adapter_creates_gemini_model(self, mock_gemini, mock_api_key, mock_llm_proxy):
        """Test AIAdapter creates Gemini model"""
        _ = AIAdapter(mock_api_key, mock_llm_proxy)

        mock_gemini.assert_called_once_with(mock_api_key, "gemini-pro", mock_llm_proxy)

    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "openai")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "gpt-4")
    @patch("src.llm.llm_manager.OpenAIModel")
    def test_ai_adapter_creates_openai_model(self, mock_openai, mock_api_key, mock_llm_proxy):
        """Test AIAdapter creates OpenAI model"""
        _ = AIAdapter(mock_api_key, mock_llm_proxy)

        mock_openai.assert_called_once_with(mock_api_key, "gpt-4", mock_llm_proxy)

    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "claude")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "claude-3-opus-20240229")
    @patch("src.llm.llm_manager.ClaudeModel")
    def test_ai_adapter_creates_claude_model(self, mock_claude, mock_api_key, mock_llm_proxy):
        """Test AIAdapter creates Claude model"""
        _ = AIAdapter(mock_api_key, mock_llm_proxy)

        mock_claude.assert_called_once_with(mock_api_key, "claude-3-opus-20240229")

    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "ollama")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "llama2")
    @patch("src.llm.llm_manager.OllamaModel")
    def test_ai_adapter_creates_ollama_model(self, mock_ollama, mock_api_key, mock_llm_proxy):
        """Test AIAdapter creates Ollama model"""
        api_url = "http://localhost:11434"
        _ = AIAdapter(mock_api_key, mock_llm_proxy, api_url)

        mock_ollama.assert_called_once_with("llama2", api_url)

    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "unsupported")
    def test_ai_adapter_raises_error_for_unsupported_model(self, mock_api_key, mock_llm_proxy):
        """Test AIAdapter raises error for unsupported model type"""
        with pytest.raises(ValueError, match="Unsupported model type"):
            AIAdapter(mock_api_key, mock_llm_proxy)

    @patch("src.llm.llm_manager.FREE_TIER", False)
    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "openai")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "gpt-4")
    @patch("src.llm.llm_manager.OpenAIModel")
    @patch("src.llm.llm_manager.pause")
    def test_ai_adapter_no_rate_limiting_when_free_tier_disabled(
        self, mock_pause, mock_openai, mock_api_key, mock_llm_proxy
    ):
        """Test AIAdapter does not apply rate limiting when free tier is disabled"""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_openai.return_value = mock_model

        adapter = AIAdapter(mock_api_key, mock_llm_proxy)

        # Make multiple requests
        for _ in range(5):
            adapter.invoke("Test prompt")

        # Verify pause was never called
        mock_pause.assert_not_called()

    @patch("src.llm.llm_manager.FREE_TIER", True)
    @patch("src.llm.llm_manager.FREE_TIER_RPM_LIMIT", 3)
    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "openai")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "gpt-4")
    @patch("src.llm.llm_manager.OpenAIModel")
    @patch("src.llm.llm_manager.pause")
    def test_ai_adapter_no_pause_under_rpm_limit(
        self, mock_pause, mock_openai, mock_api_key, mock_llm_proxy
    ):
        """Test AIAdapter does not pause when requests are under RPM limit"""
        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_openai.return_value = mock_model

        adapter = AIAdapter(mock_api_key, mock_llm_proxy)

        # Make requests under the limit (3)
        for _ in range(2):
            adapter.invoke("Test prompt")

        # Verify pause was not called
        mock_pause.assert_not_called()

    @patch("src.llm.llm_manager.FREE_TIER", True)
    @patch("src.llm.llm_manager.FREE_TIER_RPM_LIMIT", 3)
    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "openai")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "gpt-4")
    @patch("src.llm.llm_manager.OpenAIModel")
    @patch("src.llm.llm_manager.pause")
    @patch("src.llm.llm_manager.datetime")
    def test_ai_adapter_pauses_when_rpm_limit_reached(
        self, mock_datetime, mock_pause, mock_openai, mock_api_key, mock_llm_proxy
    ):
        """Test AIAdapter pauses when RPM limit is reached within 60 seconds"""
        from datetime import datetime, timedelta

        # Setup mock datetime
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.side_effect = [
            base_time,  # First request
            base_time + timedelta(seconds=10),  # Second request
            base_time + timedelta(seconds=20),  # Third request
            base_time + timedelta(seconds=30),  # Fourth request - triggers check
            base_time + timedelta(seconds=30),  # During pause calculation
        ]

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_openai.return_value = mock_model

        adapter = AIAdapter(mock_api_key, mock_llm_proxy)

        # Make requests that hit the limit (3 requests in queue, 4th triggers pause)
        for _ in range(4):
            adapter.invoke("Test prompt")

        # Verify pause was called
        # Time delta = 30 seconds since first request
        # Should pause for 60 - 30 = 30 seconds
        assert mock_pause.call_count == 1
        call_args = mock_pause.call_args[0]
        assert call_args[0] == 30.0  # pause duration
        assert call_args[1] == 31.0  # pause duration + 1

    @patch("src.llm.llm_manager.FREE_TIER", True)
    @patch("src.llm.llm_manager.FREE_TIER_RPM_LIMIT", 2)
    @patch("src.llm.llm_manager.LLM_MODEL_TYPE", "openai")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "gpt-4")
    @patch("src.llm.llm_manager.OpenAIModel")
    @patch("src.llm.llm_manager.pause")
    @patch("src.llm.llm_manager.datetime")
    def test_ai_adapter_no_pause_after_60_seconds(
        self, mock_datetime, mock_pause, mock_openai, mock_api_key, mock_llm_proxy
    ):
        """Test AIAdapter does not pause if oldest request is older than 60 seconds"""
        from datetime import datetime, timedelta

        # Setup mock datetime - requests spaced more than 60 seconds apart
        base_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.side_effect = [
            base_time,  # First request
            base_time + timedelta(seconds=30),  # Second request
            base_time + timedelta(seconds=65),  # Third request - 65 seconds after first
            base_time + timedelta(seconds=65),  # During check
        ]

        mock_model = MagicMock()
        mock_model.invoke.return_value = AIMessage(content="Test response")
        mock_openai.return_value = mock_model

        adapter = AIAdapter(mock_api_key, mock_llm_proxy)

        # Make 3 requests
        for _ in range(3):
            adapter.invoke("Test prompt")

        # Verify pause was not called since 60+ seconds passed
        mock_pause.assert_not_called()


class TestLLMLogger:
    """Tests for LLMLogger class"""

    def test_llm_logger_initialization(self, tmp_path):
        """Test LLMLogger initialization"""
        with patch("src.llm.llm_manager.LOG_DIR", str(tmp_path)):
            logger = LLMLogger()
            assert logger.calls_log == str(tmp_path / "llm_api_calls.yaml")

    @patch("src.llm.llm_manager.append_yaml_file")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "gpt-4")
    @patch("src.llm.llm_manager.LOG_DIR", "/tmp/logs")
    def test_llm_logger_log_request_with_string_prompt(self, mock_append_yaml):
        """Test LLMLogger log_request with StringPromptValue - currently fails due to bug"""
        logger = LLMLogger()

        # StringPromptValue gets converted to .text (string) but LLMCall expects Dict
        prompts = StringPromptValue(text="Test prompt")
        parsed_reply = {
            "content": "Test response",
            "response_metadata": {"model_name": "gpt-4"},
            "usage_metadata": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        }

        # This will fail because LLMCall validation expects Dict[str, str] for prompts
        logger.log_request(prompts, parsed_reply)

        # Verify append_yaml_file was called
        mock_append_yaml.assert_called_once()
        call_args = mock_append_yaml.call_args[0][1]

        assert call_args["model_name"] == "gpt-4"
        assert call_args["input_tokens"] == 100
        assert call_args["output_tokens"] == 50
        assert call_args["total_tokens"] == 150

    @patch("src.llm.llm_manager.append_yaml_file")
    @patch("src.llm.llm_manager.EASY_APPLY_MODEL", "gpt-4")
    @patch("src.llm.llm_manager.LOG_DIR", "/tmp/logs")
    def test_llm_logger_log_request_with_dict_prompts(self, mock_append_yaml):
        """Test LLMLogger log_request with Dict prompts"""
        logger = LLMLogger()

        mock_message = MagicMock()
        mock_message.content = "Test prompt content"
        prompts = MagicMock()
        prompts.messages = [mock_message]

        parsed_reply = {
            "content": "Test response",
            "response_metadata": {"model_name": "gpt-4"},
            "usage_metadata": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        }

        logger.log_request(prompts, parsed_reply)

        mock_append_yaml.assert_called_once()


class TestLoggerChatModel:
    """Tests for LoggerChatModel class"""

    @patch("src.llm.llm_manager.LLMLogger")
    def test_logger_chat_model_initialization(self, mock_llm_logger_class):
        """Test LoggerChatModel initialization"""
        mock_llm = MagicMock()
        chat_model = LoggerChatModel(mock_llm)

        assert chat_model.llm == mock_llm
        mock_llm_logger_class.assert_called_once()

    @patch("src.llm.llm_manager.LLMLogger")
    def test_logger_chat_model_call_success(self, mock_llm_logger_class):
        """Test LoggerChatModel __call__ method success"""
        mock_llm = MagicMock()
        mock_reply = AIMessage(
            content="Test response",
            response_metadata={"model_name": "gpt-4"},
            usage_metadata={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        )
        mock_llm.invoke.return_value = mock_reply

        chat_model = LoggerChatModel(mock_llm)
        messages = [{"role": "user", "content": "Test prompt"}]

        response = chat_model(messages)

        assert response == mock_reply
        mock_llm.invoke.assert_called_once_with(messages)

    def test_logger_chat_model_parse_llm_result_with_usage_metadata(self):
        """Test LoggerChatModel parse_llmresult with usage_metadata"""
        mock_llm = MagicMock()
        chat_model = LoggerChatModel(mock_llm)

        llmresult = AIMessage(
            content="Test response",
            id="test-id",
            response_metadata={
                "model_name": "gpt-4",
                "finish_reason": "stop",
            },
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )

        parsed = chat_model.parse_llmresult(llmresult)

        assert parsed["content"] == "Test response"
        assert parsed["response_metadata"]["model_name"] == "gpt-4"
        assert parsed["usage_metadata"]["input_tokens"] == 100
        assert parsed["usage_metadata"]["output_tokens"] == 50
        assert parsed["usage_metadata"]["total_tokens"] == 150


class TestGPTAnswerer:
    """Tests for GPTAnswerer class"""

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_initialization(
        self, mock_logger_chat, mock_ai_adapter, mock_api_key, mock_llm_proxy
    ):
        """Test GPTAnswerer initialization"""
        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)

        mock_ai_adapter.assert_called_once_with(mock_api_key, mock_llm_proxy, None)
        assert answerer.job is None

    def test_gpt_answerer_find_best_match_exact(self):
        """Test GPTAnswerer find_best_match with exact match"""
        options = ["Python", "Java", "JavaScript"]
        text = "Python"

        result = GPTAnswerer.find_best_match(text, options)
        assert result == "Python"

    def test_gpt_answerer_find_best_match_fuzzy(self):
        """Test GPTAnswerer find_best_match with fuzzy match"""
        options = ["Python", "Java", "JavaScript"]
        text = "Pythn"  # Typo

        result = GPTAnswerer.find_best_match(text, options)
        assert result == "Python"

    def test_gpt_answerer_find_best_match_no_info(self):
        """Test GPTAnswerer find_best_match with 'no info'"""
        options = ["Python", "Java", "JavaScript"]
        text = "no info"

        result = GPTAnswerer.find_best_match(text, options)
        assert result == "no info"

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_set_resume(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
    ):
        """Test GPTAnswerer set_resume method"""
        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.set_resume(mock_resume_structured, mock_resume_readable)

        assert answerer.resume_structured == mock_resume_structured
        assert answerer.resume_readable == mock_resume_readable

    @patch("src.llm.llm_manager.transform_vacancy_data")
    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_set_job(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_transform,
        mock_api_key,
        mock_llm_proxy,
        mock_job,
    ):
        """Test GPTAnswerer set_job method"""
        mock_transform.return_value = "Transformed job data"

        # Mock the summarize chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Brief job description"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains["summarize_job_description"] = mock_chain
        answerer.set_job(mock_job)

        assert answerer.job == mock_job
        assert answerer.job_readable == "Brief job description"
        mock_transform.assert_called_once_with(mock_job)

    @patch("src.llm.llm_manager.transform_search_config_data")
    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_set_search_parameters(
        self, mock_logger_chat, mock_ai_adapter, mock_transform, mock_api_key, mock_llm_proxy
    ):
        """Test GPTAnswerer set_search_parameters method"""
        mock_transform.return_value = "Transformed search params"
        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        params = {"remote": True, "positions": ["Python Developer"]}

        answerer.set_search_parameters(params)

        assert answerer.search_parameters == "Transformed search params"
        mock_transform.assert_called_once_with(params)

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_clean_html_response(
        self, mock_logger_chat, mock_ai_adapter, mock_api_key, mock_llm_proxy
    ):
        """Test GPTAnswerer _clean_html_response method"""
        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)

        # Test with markdown wrapper
        html = "```html\n<div>Test</div>\n```"
        result = answerer._clean_html_response(html)
        assert result == "<div>Test</div>"

        # Test without wrapper
        html = "<div>Test</div>"
        result = answerer._clean_html_response(html)
        assert result == "<div>Test</div>"

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_answer_question_numeric_with_no_info(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
    ):
        """Test GPTAnswerer answer_question_numeric with 'no info' response"""
        # Setup mock chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "no info"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains = {"numeric_question": mock_chain}
        answerer.set_resume(mock_resume_structured, mock_resume_readable)

        result = answerer.answer_question_numeric("How many years of experience?", [])

        assert result == "no info"

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_answer_question_numeric_with_number(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
    ):
        """Test GPTAnswerer answer_question_numeric with numeric response"""
        # Setup mock chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "5 years"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains = {"numeric_question": mock_chain}
        answerer.set_resume(mock_resume_structured, mock_resume_readable)

        result = answerer.answer_question_numeric("How many years of experience?", [])

        assert result == "5"

    @patch("src.llm.llm_manager.ChatPromptTemplate")
    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_select_many_answers_from_options(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_chat_prompt,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
    ):
        """Test GPTAnswerer select_many_answers_from_options method"""
        # Setup mock LLM to return string
        mock_llm_instance = MagicMock()
        mock_llm_instance.return_value = "Python; JavaScript; AWS"
        mock_logger_chat.return_value = mock_llm_instance

        # Setup mock prompt template and chain
        mock_prompt = MagicMock()
        mock_parser = MagicMock()
        mock_parser.parse.return_value = "Python; JavaScript; AWS"

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Python; JavaScript; AWS"

        mock_prompt.__or__ = MagicMock()
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_chat_prompt.from_template.return_value = mock_prompt

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.set_resume(mock_resume_structured, mock_resume_readable)

        options = ["Python", "JavaScript", "Java", "AWS", "Docker"]
        result = answerer.select_many_answers_from_options("Select your skills", options, [])

        assert len(result) == 3
        assert "Python" in result
        assert "JavaScript" in result
        assert "AWS" in result

    @patch("src.llm.llm_manager.JOB_IS_INTERESTING_THRESH", 70)
    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_job_is_interesting_true(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
        mock_job,
    ):
        """Test GPTAnswerer job_is_interesting returns True"""
        # Setup mock chain for job_is_interesting
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Score: 85\nReasoning: Great match for skills"

        # Setup mock chain for summarize_job_description
        mock_summarize_chain = MagicMock()
        mock_summarize_chain.invoke.return_value = "Brief job description"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains["job_is_interesting"] = mock_chain
        answerer.chains["summarize_job_description"] = mock_summarize_chain
        answerer.set_resume(mock_resume_structured, mock_resume_readable)
        answerer.set_job(mock_job)
        answerer.search_parameters = "Remote: True"

        is_interesting, score, reasoning = answerer.job_is_interesting(mock_job)

        assert is_interesting is True
        assert score == "85"
        assert "Great match" in reasoning

    @patch("src.llm.llm_manager.JOB_IS_INTERESTING_THRESH", 70)
    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_job_is_interesting_false(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
        mock_job,
    ):
        """Test GPTAnswerer job_is_interesting returns False"""
        # Setup mock chain for job_is_interesting
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Score: 50\nReasoning: Not a good fit"

        # Setup mock chain for summarize_job_description
        mock_summarize_chain = MagicMock()
        mock_summarize_chain.invoke.return_value = "Brief job description"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains["job_is_interesting"] = mock_chain
        answerer.chains["summarize_job_description"] = mock_summarize_chain
        answerer.set_resume(mock_resume_structured, mock_resume_readable)
        answerer.set_job(mock_job)
        answerer.search_parameters = "Remote: True"

        is_interesting, score, reasoning = answerer.job_is_interesting(mock_job)

        assert is_interesting is False
        assert score == "50"
        assert "Not a good fit" in reasoning

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_write_cover_letter(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
        mock_job,
    ):
        """Test GPTAnswerer write_cover_letter method"""
        # Setup mock chain for cover letter
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Dear Hiring Manager,\n\nI am writing..."

        # Setup mock chain for summarize_job_description
        mock_summarize_chain = MagicMock()
        mock_summarize_chain.invoke.return_value = "Brief job description"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains["summarize_job_description"] = mock_summarize_chain
        answerer.chains["prompt_cover_letter"] = mock_chain
        answerer.set_resume(mock_resume_structured, mock_resume_readable)
        answerer.set_job(mock_job)

        result = answerer.write_cover_letter()

        assert "Dear Hiring Manager" in result

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_parse_resume(
        self, mock_logger_chat, mock_ai_adapter, mock_api_key, mock_llm_proxy
    ):
        """Test GPTAnswerer parse_resume method"""

        # Create a mock parsed output
        mock_resume_obj = MagicMock()
        mock_resume_obj.model_dump.return_value = {
            "personal_information": {"first_name": "John", "last_name": "Doe"}
        }

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = mock_resume_obj

        mock_parser = MagicMock()
        mock_parser.get_format_instructions.return_value = "Format instructions"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains = {"parse_resume": (mock_chain, mock_parser)}

        resume_text = "John Doe\nSoftware Engineer"
        result = answerer.parse_resume(resume_text)

        assert "personal_information" in result
        assert result["personal_information"]["first_name"] == "John"

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_gpt_answerer_generate_html_resume(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
        mock_job,
    ):
        """Test GPTAnswerer generate_html_resume method"""
        # Setup mock chain for summarize_job_description
        mock_summarize_chain = MagicMock()
        mock_summarize_chain.invoke.return_value = "Brief job description"

        # Setup mock methods
        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains["summarize_job_description"] = mock_summarize_chain
        answerer.set_resume(mock_resume_structured, mock_resume_readable)
        answerer.set_job(mock_job)

        # Mock load_resume_template to return empty string so generate methods are called
        answerer.load_resume_template = MagicMock(return_value="")
        answerer.save_resume_template = MagicMock()

        answerer.generate_header = MagicMock(return_value="<header>Header</header>")
        answerer.generate_education_section = MagicMock(return_value="<section>Education</section>")
        answerer.generate_work_experience_section = MagicMock(
            return_value="<section>Experience</section>"
        )
        answerer.generate_side_projects_section = MagicMock(return_value="")
        answerer.generate_achievements_section = MagicMock(return_value="")
        answerer.generate_certifications_section = MagicMock(return_value="")
        answerer.generate_additional_skills_section = MagicMock(
            return_value="<section>Skills</section>"
        )

        result = answerer.generate_html_resume()

        assert "<body>" in result
        assert "</body>" in result
        assert "Header" in result
        assert "Education" in result
        assert "Experience" in result
        assert "Skills" in result


class TestGPTAnswererIntegration:
    """Integration tests for GPTAnswerer that test method interactions"""

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_answer_question_textual_wide_range(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
    ):
        """Test GPTAnswerer answer_question_textual_wide_range method"""
        # Setup mock chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "I have 5 years of Python experience"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains = {"text_question": mock_chain}
        answerer.set_resume(mock_resume_structured, mock_resume_readable)

        result = answerer.answer_question_textual_wide_range(
            "How many years of Python experience do you have?", []
        )

        assert "Python experience" in result
        mock_chain.invoke.assert_called_once()

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_answer_question_with_error(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
    ):
        """Test GPTAnswerer answer_question_textual_wide_range_with_error method"""
        # Setup mock chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "5 years"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains = {"text_question_with_error": mock_chain}
        answerer.set_resume(mock_resume_structured, mock_resume_readable)

        result = answerer.answer_question_textual_wide_range_with_error(
            question="How many years of experience?",
            error="Answer must be numeric",
            previous_answer="five",
            previous_questions=[],
        )

        assert result == "5 years"
        mock_chain.invoke.assert_called_once()

    @patch("src.llm.llm_manager.ChatPromptTemplate")
    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_select_one_answer_from_options(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_chat_prompt,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
    ):
        """Test GPTAnswerer select_one_answer_from_options method"""
        # Setup mock LLM to return string
        mock_llm_instance = MagicMock()
        mock_llm_instance.return_value = "Python"
        mock_logger_chat.return_value = mock_llm_instance

        # Setup mock prompt template and chain
        mock_prompt = MagicMock()
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Python"

        mock_prompt.__or__ = MagicMock()
        mock_prompt.__or__.return_value.__or__ = MagicMock(return_value=mock_chain)

        mock_chat_prompt.from_template.return_value = mock_prompt

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.set_resume(mock_resume_structured, mock_resume_readable)

        options = ["Python", "Java", "JavaScript"]
        result = answerer.select_one_answer_from_options(
            "What is your primary language?", options, []
        )

        assert result == "Python"

    @patch("src.llm.llm_manager.AIAdapter")
    @patch("src.llm.llm_manager.LoggerChatModel")
    def test_resume_improvement_recommendations(
        self,
        mock_logger_chat,
        mock_ai_adapter,
        mock_api_key,
        mock_llm_proxy,
        mock_resume_structured,
        mock_resume_readable,
    ):
        """Test GPTAnswerer resume_improvement_recommendations method"""
        # Setup mock chain
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Consider adding more quantifiable achievements"

        answerer = GPTAnswerer(mock_api_key, mock_llm_proxy)
        answerer.chains = {"resume_improvement": mock_chain}
        answerer.set_resume(mock_resume_structured, mock_resume_readable)

        result = answerer.resume_improvement_recommendations()

        assert "quantifiable achievements" in result
        mock_chain.invoke.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
