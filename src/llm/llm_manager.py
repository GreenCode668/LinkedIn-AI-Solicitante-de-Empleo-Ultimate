import os
import re
import textwrap
import traceback
from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.messages.ai import AIMessage
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompt_values import StringPromptValue
from langchain_core.prompts import ChatPromptTemplate
from Levenshtein import distance
from pydantic import BaseModel

import src.llm.prompts as prompts
from config.app_config import (
    EASY_APPLY_MODEL,
    FREE_TIER,
    FREE_TIER_RPM_LIMIT,
    JOB_IS_INTERESTING_THRESH,
    LLM_MODEL_TYPE,
    TEMPERATURE,
)
from config.constants import LOG_DIR, RESUME_DIR, cost_per_token
from config.logger_config import logger
from src.pydantic_models.log_models import LLMCall
from src.pydantic_models.prompt_models import ResumeStructure
from src.utils.json_to_readable import transform_search_config_data, transform_vacancy_data
from src.utils.utils import append_yaml_file, pause

load_dotenv()


class AIModel(ABC):
    @abstractmethod
    def invoke(self, prompt: str) -> str:
        pass


class GeminiModel(AIModel):
    """Get access to Gemini model"""

    def __init__(self, api_key: str, llm_model: str, llm_proxy: str = None) -> None:
        from google.genai import types
        from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory

        # os.environ["https_proxy"] = llm_proxy
        http_options = types.HttpOptions(
            client_args={"proxy": llm_proxy}, async_client_args={"proxy": llm_proxy}
        )
        self.google_api_key = api_key
        self.model = ChatGoogleGenerativeAI(
            model=llm_model,
            google_api_key=self.google_api_key,
            temperature=TEMPERATURE,
            thinking_level="minimal",
            safety_settings={
                HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DEROGATORY: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_TOXICITY: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_VIOLENCE: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUAL: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_MEDICAL: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            },
            http_options=http_options,
        )

    def invoke(self, prompt: ChatPromptTemplate) -> BaseMessage:
        logger.info("Got access to model via Gemini API")
        prompt_messages = [SystemMessage(content=prompts.custom_instructions)] + prompt.messages
        # randomly select one proxy after another until LLM request succeeds
        response = self.model.invoke(prompt_messages)
        return response


class OpenAIModel(AIModel):
    """Get access to OpenAI model"""

    def __init__(self, api_key: str, llm_model: str, llm_proxy: str = None) -> None:
        from langchain_openai import ChatOpenAI

        if llm_proxy:
            http_client = httpx.Client(proxy=llm_proxy)
        else:
            http_client = None
        self.llm_proxy = llm_proxy
        self.model_name = llm_model
        self.openai_api_key = api_key
        is_reasoning_model = (
            "o1" in self.model_name
            or "o3" in self.model_name
            or "o4" in self.model_name
            or "gpt-5" in self.model_name
        )
        extra = {"reasoning_effort": "minimal"} if is_reasoning_model else {}
        self.model = ChatOpenAI(
            model_name=self.model_name,
            openai_api_key=self.openai_api_key,
            http_client=http_client,
            temperature=1 if is_reasoning_model or "gpt-5" in self.model_name else TEMPERATURE,
            presence_penalty=0,
            frequency_penalty=0,
            timeout=60,
            **extra,
        )

    def invoke(self, prompt: ChatPromptTemplate) -> BaseMessage:
        logger.info("Got access to model via OpenAI API")
        prompt_messages = [SystemMessage(content=prompts.custom_instructions)] + prompt.messages
        response = self.model.invoke(prompt_messages)
        return response


class ClaudeModel(AIModel):
    """Get access to Claude model"""

    def __init__(self, api_key: str, llm_model: str) -> None:
        from langchain_anthropic import ChatAnthropic

        self.model = ChatAnthropic(model=llm_model, api_key=api_key, temperature=TEMPERATURE)

    def invoke(self, prompt: str) -> BaseMessage:
        response = self.model.invoke(prompt)
        logger.debug("Successfully got access to model via Claude API")
        return response


class OllamaModel(AIModel):
    """Get access to Ollama model"""

    def __init__(self, llm_model: str, llm_api_url: str) -> None:
        from langchain_ollama import ChatOllama

        if llm_api_url:
            logger.debug(f"Using Ollama with API URL: {llm_api_url}")
            self.model = ChatOllama(model=llm_model, base_url=llm_api_url)
        else:
            self.model = ChatOllama(model=llm_model)

    def invoke(self, prompt: str) -> BaseMessage:
        response = self.model.invoke(prompt)
        logger.debug("Successfully got access to model via Ollama API")
        return response


class OpenRouterModel(AIModel):
    """Get access to models via OpenRouter API"""

    def __init__(self, api_key: str, llm_model: str, llm_proxy: str = None) -> None:
        from langchain_openai import ChatOpenAI

        http_client = httpx.Client(proxy=llm_proxy) if llm_proxy else None
        self.llm_proxy = llm_proxy
        self.model_name = llm_model
        self.model = ChatOpenAI(
            model_name=self.model_name,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            http_client=http_client,
            temperature=TEMPERATURE,
            timeout=60,
        )

    def invoke(self, prompt: ChatPromptTemplate) -> BaseMessage:
        logger.info("Got access to model via OpenRouter API")
        prompt_messages = [SystemMessage(content=prompts.custom_instructions)] + prompt.messages
        response = self.model.invoke(prompt_messages)
        return response


# class xAIModel(AIModel):
#     """Get access to xAI model"""

#     def __init__(self, api_key: str, llm_model: str) -> None:
#         from langchain_xai import ChatXAI

#         self.model = ChatXAI(model=llm_model, xai_api_key=api_key)

#     def invoke(self, prompt: str) -> BaseMessage:
#         response = self.model.invoke(prompt)
#         logger.debug("Successfully got access to model via Ollama API")
#         return response


# class HuggingFaceModel(AIModel):
#     """Get access to Hugging Face model"""

#     def __init__(self, api_key: str, llm_model: str) -> None:
#         from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

#         self.model = HuggingFaceEndpoint(
#             repo_id=llm_model, huggingfacehub_api_token=api_key, temperature=TEMPERATURE
#         )
#         self.chatmodel = ChatHuggingFace(llm=self.model)

#     def invoke(self, prompt: str) -> BaseMessage:
#         response = self.chatmodel.invoke(prompt)
#         logger.debug("Successfully got access to model via Hugging Face API")
#         return response


class AIAdapter:
    """Class for accessing LLM models from different companies via API"""

    def __init__(self, api_key: str = None, llm_proxy: str = None, llm_api_url: str = None):
        self.model_type = LLM_MODEL_TYPE
        self.easy_apply_model = EASY_APPLY_MODEL
        self.free_tier = FREE_TIER
        self.free_tier_rpm_limit = FREE_TIER_RPM_LIMIT
        self.free_tier_request_queue = deque(maxlen=self.free_tier_rpm_limit)
        self.model = self._create_model(api_key, llm_proxy, llm_api_url)

    def _create_model(self, api_key: str, llm_proxy: str, llm_api_url: str) -> AIModel:
        logger.info(f"Using {self.model_type} from {self.easy_apply_model}")

        if self.model_type == "gemini":
            if not api_key:
                raise ValueError("API key is required for Gemini model")
            return GeminiModel(api_key, self.easy_apply_model, llm_proxy)
        elif self.model_type == "openai":
            if not api_key:
                raise ValueError("API key is required for OpenAI model")
            return OpenAIModel(api_key, self.easy_apply_model, llm_proxy)
        elif self.model_type == "claude":
            if not api_key:
                raise ValueError("API key is required for Claude model")
            return ClaudeModel(api_key, self.easy_apply_model)
        elif self.model_type == "ollama":
            return OllamaModel(self.easy_apply_model, llm_api_url)
        elif self.model_type == "openrouter":
            return OpenRouterModel(api_key, self.easy_apply_model, llm_proxy)
        # elif self.model_type == "xai":
        #     return xAIModel(api_key, self.easy_apply_model)
        # elif self.model_type == "huggingface":
        #     return HuggingFaceModel(api_key, self.easy_apply_model)
        else:
            raise ValueError(f"Unsupported model type: {LLM_MODEL_TYPE}")

    def invoke(self, prompt: str) -> str:
        if self.free_tier:
            # if free tier mode is activated and current model RPM is greater than the limit,
            # wait for the specified time before invoking the model to avoid rate limit errors
            if len(self.free_tier_request_queue) >= self.free_tier_rpm_limit:
                first_request_timestamp = self.free_tier_request_queue.popleft()
                time_delta = datetime.now() - first_request_timestamp
                if time_delta < timedelta(seconds=60):
                    pause(60 - time_delta.total_seconds(), 60 - time_delta.total_seconds() + 1)
            self.free_tier_request_queue.append(datetime.now())
        return self.model.invoke(prompt)


class LLMLogger:
    """Class for logging all events that occur when working with LLM"""

    def __init__(self):
        self.calls_log = os.path.join(Path(LOG_DIR), "llm_api_calls.yaml")
        logger.info("LLMLogger successfully initialized")

    def log_request(self, prompts, parsed_reply: Dict[str, Dict]) -> None:
        """Method for logging all LLM operations"""
        logger.debug("Starting execution of log_request method")
        logger.debug("Prompts received")
        logger.debug("Parsed response received")

        try:
            logger.debug(f"Log file path determined: {self.calls_log}")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Error determining log file path: {tb_str}")
            raise

        if isinstance(prompts, StringPromptValue):
            logger.debug("Prompts have StringPromptValue type")
            prompts = {"prompt_1": prompts.text}
        elif isinstance(prompts, Dict):
            logger.debug("Prompts have Dict type")
            try:
                prompts = {
                    f"prompt_{i + 1}": prompt.content for i, prompt in enumerate(prompts.messages)
                }
                logger.debug("Prompts converted to dictionary")
            except Exception:
                tb_str = traceback.format_exc()
                logger.error(f"Error converting prompts to dictionary: {tb_str}")
                raise
        else:
            logger.debug("Unknown prompt type, attempting default conversion")
            try:
                prompts = {
                    f"prompt_{i + 1}": prompt.content for i, prompt in enumerate(prompts.messages)
                }
                logger.debug("Prompts converted to dictionary using default method")
            except Exception:
                tb_str = traceback.format_exc()
                logger.error(f"Error converting prompts using default method: {tb_str}")
                raise

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            token_usage = parsed_reply["usage_metadata"]
            output_tokens = token_usage["output_tokens"]
            input_tokens = token_usage["input_tokens"]
            total_tokens = token_usage["total_tokens"]
            logger.info(
                f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}"
            )
        except KeyError as e:
            logger.error(f"Key error in parsed_reply structure: {str(e)}")
            raise

        try:
            model_name = parsed_reply["response_metadata"]["model_name"]
            logger.debug(f"Model name: {model_name}")
        except KeyError as e:
            logger.error(f"Key error in response_metadata: {str(e)}")
            raise

        prompt_cost, completion_cost = cost_per_token(
            model=EASY_APPLY_MODEL.replace("google/", ""),
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        )
        total_cost = prompt_cost + completion_cost
        logger.info(f"Total cost calculated: {total_cost}")

        try:
            log_entry = LLMCall(
                model_name=model_name,
                timestamp=current_time,
                prompts=prompts,
                parsed_reply=parsed_reply["content"],
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=total_cost,
            )
            logger.debug(f"Log entry created: {log_entry}")
        except KeyError as e:
            logger.error(f"Error creating log entry: missing key {str(e)} in parsed_reply")
            raise

        # Append the log entry to the call log file
        append_yaml_file(Path(self.calls_log), log_entry.model_dump())
        logger.info(f"LLM call log entry appended to {self.calls_log}")


class LoggerChatModel:
    """
    Class for interacting with language model (LLM) and logging all operations.
    This class processes requests to the language model, parses and logs responses, and handles
    possible errors such as rate limit exceeded or network errors.
    """

    def __init__(self, llm: GeminiModel):
        self.llm = llm
        self.llm_logger = LLMLogger()
        logger.info(f"LoggerChatModel successfully initialized, LLM: {llm}")

    def __call__(self, messages: List[Dict[str, str]]) -> str:
        """
        Execute LLM call, process response and log the entire process.
        """
        # logger.debug(f"Entering __call__ method with messages: {messages}")
        while True:
            try:
                logger.info("Attempting LLM call")

                reply = self.llm.invoke(messages)
                logger.debug(f"Response from LLM: {reply}")

                parsed_reply = self.parse_llmresult(reply)
                logger.info(f"Successfully parsed LLM result: {parsed_reply}")

                self.llm_logger.log_request(prompts=messages, parsed_reply=parsed_reply)

                return reply

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTPStatusError occurred: {str(e)}")
                if e.response.status_code == 429:
                    retry_after = e.response.headers.get("retry-after")
                    retry_after_ms = e.response.headers.get("retry-after-ms")

                    if retry_after:
                        wait_time = int(retry_after)
                        logger.warning(
                            f"Rate limit exceeded. Waiting {wait_time} seconds before retry (from 'retry-after' header)..."
                        )
                        pause(wait_time, wait_time + 1)
                    elif retry_after_ms:
                        wait_time = int(retry_after_ms) / 1000.0
                        logger.warning(
                            f"Rate limit exceeded. Waiting {wait_time} seconds before retry (from 'retry-after-ms' header)..."
                        )
                        pause(wait_time, wait_time + 1)
                    else:
                        wait_time = 30
                        logger.warning(
                            f"'retry-after' header not found. Waiting {wait_time} seconds before retry (default)..."
                        )
                        pause(wait_time, wait_time + 1)
                else:
                    logger.error(
                        f"HTTP error occurred with status: {e.response.status_code}, waiting 30 seconds before retry"
                    )
                    pause(30, 31)

    def parse_llmresult(self, llmresult: AIMessage) -> Dict[str, Dict]:
        """Parse LLM result"""
        logger.info("Parsing LLM result")

        try:
            if hasattr(llmresult, "usage_metadata") and llmresult.usage_metadata is not None:
                content = llmresult.content
                response_metadata = llmresult.response_metadata
                id_ = llmresult.id
                usage_metadata = llmresult.usage_metadata

                parsed_result = {
                    "content": content,
                    "response_metadata": {
                        "model_name": response_metadata.get("model_name", ""),
                        "system_fingerprint": response_metadata.get("system_fingerprint", ""),
                        "finish_reason": response_metadata.get("finish_reason", ""),
                        "logprobs": response_metadata.get("logprobs", None),
                    },
                    "id": id_,
                    "usage_metadata": {
                        "input_tokens": usage_metadata.get("input_tokens", 0),
                        "output_tokens": usage_metadata.get("output_tokens", 0),
                        "total_tokens": usage_metadata.get("total_tokens", 0),
                    },
                }
            else:
                try:
                    content = llmresult.content
                    response_metadata = llmresult.response_metadata
                    id_ = llmresult.id

                    # Handle the case where token_usage might not be in response_metadata
                    if "token_usage" in response_metadata:
                        token_usage = response_metadata["token_usage"]
                        input_tokens = token_usage.prompt_tokens
                        output_tokens = token_usage.completion_tokens
                        total_tokens = token_usage.total_tokens
                    else:
                        # Default values when token_usage is not available
                        input_tokens = 0
                        output_tokens = 0
                        total_tokens = 0

                    parsed_result = {
                        "content": content,
                        "response_metadata": {
                            "model_name": response_metadata.get("model", ""),
                            "finish_reason": response_metadata.get("finish_reason", ""),
                        },
                        "id": id_,
                        "usage_metadata": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": total_tokens,
                        },
                    }
                except Exception:
                    tb_str = traceback.format_exc()
                    logger.error(f"Error processing result without usage_metadata: {tb_str}")
                    # Create a minimal parsed result with defaults
                    parsed_result = {
                        "content": llmresult.content if hasattr(llmresult, "content") else "",
                        "response_metadata": {"model_name": "unknown", "finish_reason": "unknown"},
                        "id": llmresult.id if hasattr(llmresult, "id") else "",
                        "usage_metadata": {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                        },
                    }
            return parsed_result

        except KeyError as e:
            logger.error(f"KeyError when parsing LLM result: missing key {str(e)}")
            raise

        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Unexpected error when parsing LLM result: {tb_str}")
            raise


class GPTAnswerer:
    """
    Class for processing resume questions and generating answers using LLM.
    The class includes methods for processing and determining resume sections such as
    personal information, work experience, etc., based on provided questions.
    Designed for automating resume question responses,
    as well as writing cover letters.
    """

    def __init__(self, llm_api_key: str = None, llm_proxy: str = None, llm_api_url: str = None):
        self.job = None
        self.ai_adapter = AIAdapter(llm_api_key, llm_proxy, llm_api_url)
        self.llm_cheap = LoggerChatModel(self.ai_adapter)
        self.resume_template_dir = Path(RESUME_DIR) / "templates"
        self.chains = {
            "parse_resume": self._create_pydantic_chain(
                prompts.parse_resume_template, ResumeStructure
            ),
            "resume_improvement": self._create_chain(prompts.resume_improve),
            "extract_skills_from_vacancy": self._create_chain(prompts.extract_skills_from_vacancy),
            "summarize_job_description": self._create_chain(prompts.summarize_prompt_template),
            "job_is_interesting": self._create_chain(prompts.job_is_interesting),
            "text_question": self._create_chain(prompts.text_question_answer_template),
            "numeric_question": self._create_chain(prompts.numeric_question_template),
            "text_question_with_error": self._create_chain(
                prompts.text_question_with_error_template
            ),
            "prompt_cover_letter": self._create_chain(prompts.coverletter_template),
            "prompt_header": self._create_chain(prompts.prompt_header),
            "prompt_education": self._create_chain(prompts.prompt_education),
            "prompt_working_experience": self._create_chain(prompts.prompt_working_experience),
            "prompt_side_projects": self._create_chain(prompts.prompt_side_projects),
            "prompt_achievements": self._create_chain(prompts.prompt_achievements),
            "prompt_certifications": self._create_chain(prompts.prompt_certifications),
            "prompt_additional_skills": self._create_chain(prompts.prompt_additional_skills),
        }

    @staticmethod
    def find_best_match(text: str, options: list[str]) -> str:
        """
        Find the best match for a string with one of the options
        and return the best option from the list.
        """
        if "no info" in text.lower():
            return "no info"
        logger.info(f"Searching for best match for text: '{text}' in options: {options}")
        distances = [(option, distance(text.lower(), option.lower())) for option in options]
        best_option = min(distances, key=lambda x: x[1])[0]
        logger.info(f"Best match found: {best_option}")
        return best_option

    @staticmethod
    def _remove_placeholders(text: str) -> str:
        """Remove all 'PLACEHOLDER' placeholders from text."""
        logger.debug("Removing placeholders from text")
        return text.replace("PLACEHOLDER", "").strip()

    @staticmethod
    def _preprocess_template_string(template: str) -> str:
        """Transform template string for use in prompts."""
        logger.debug("Preprocessing template string")
        return textwrap.dedent(template)

    @staticmethod
    def _clean_html_response(html_response: str) -> str:
        """Clean HTML response by removing markdown code block wrappers"""
        # Remove markdown code block wrappers
        html_response = html_response.strip()

        # Remove ```html at the beginning
        if html_response.startswith("```html"):
            html_response = html_response[7:]  # Remove "```html"

        # Remove ``` at the end
        if html_response.endswith("```"):
            html_response = html_response[:-3]  # Remove "```"

        # Remove any remaining ```html patterns that might be in the middle
        html_response = html_response.replace("```html", "").replace("```", "")

        return html_response.strip()

    def set_resume(self, resume_structured: Dict[str, Any], resume_readable: str) -> None:
        """Add resume for analysis."""
        logger.info("Adding resume")
        self.resume_structured = resume_structured
        self.resume_readable = resume_readable

    def set_job(self, job: Dict[str, Any], is_test: bool = False) -> None:
        """Add job description."""
        self.job = job
        text = transform_vacancy_data(job)
        if is_test:
            self.job_readable = text
        else:
            self.job_readable = self.summarize_job_description(text)
        logger.info(f"Adding job description: {self.job_readable}")

    def set_search_parameters(self, parameters: dict) -> None:
        """Set job search parameters."""
        logger.info(f"Setting job search parameters: {parameters}")
        self.search_parameters = transform_search_config_data(parameters)

    def _create_chain(self, template: str) -> ChatPromptTemplate:
        """Create a chain for a specific resume section."""
        template = self._preprocess_template_string(template)
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm_cheap | StrOutputParser()

    def _create_pydantic_chain(
        self, template: str, pydantic_object: BaseModel
    ) -> Tuple[ChatPromptTemplate, PydanticOutputParser]:
        """Create a chain for a specific resume section."""
        parser = PydanticOutputParser(pydantic_object=pydantic_object)
        template = self._preprocess_template_string(template)
        prompt = ChatPromptTemplate.from_template(template)
        return prompt | self.llm_cheap | parser, parser

    def parse_resume(self, resume_text: str) -> Dict[str, Any]:
        """Parse resume using Pydantic models for structured output."""
        logger.info("Parsing resume with structured output")
        chain, parser = self.chains["parse_resume"]
        output = chain.invoke(
            {"resume": resume_text, "format_instructions": parser.get_format_instructions()}
        )
        logger.debug(f"Structured resume parsing completed: {output}")
        return output.model_dump()

    def extract_skills_from_vacancy(self, job_description: str) -> list[str]:
        """Extract skills from vacancy"""
        chain = self.chains["extract_skills_from_vacancy"]
        output = chain.invoke({"job_description": job_description})
        output = output.replace("[", "").replace("]", "")
        output = output.replace("'", "").replace('"', "")
        output = output.split(",")
        output = [skill.strip() for skill in output if skill.strip()]
        logger.debug(f"Skills extracted from vacancy: {output}")
        return output

    def summarize_job_description(self, text: str) -> str:
        """Create brief job description"""
        logger.info(f"Creating brief job description: '{text}'")
        chain = self.chains["summarize_job_description"]
        output = chain.invoke({"text": text})
        logger.debug(f"Generated brief description: {output}")
        return output

    def answer_question_textual_wide_range(
        self, question: str, previous_questions: list[str]
    ) -> str:
        """Determine the topic of the given question and answer it"""
        current_date = datetime.now().date().strftime("%Y-%m-%d")
        gender = self.resume_structured["personal_information"].get("gender")
        chain = self.chains["text_question"]
        output = chain.invoke(
            {
                "resume": self.resume_readable,
                "question": question,
                "current_date": current_date,
                "gender": gender,
                "previous_questions": previous_questions,
            }
        )
        logger.debug(f"Answer to question: {output}")
        return output

    def answer_question_textual_wide_range_with_error(
        self, question: str, error: str, previous_answer: str, previous_questions: list[str]
    ) -> str:
        """Answer question with error"""
        current_date = datetime.now().date().strftime("%Y-%m-%d")
        chain = self.chains["text_question_with_error"]
        output = chain.invoke(
            {
                "resume": self.resume_readable,
                "question": question,
                "previous_answer": previous_answer,
                "error": error,
                "current_date": current_date,
                "previous_questions": previous_questions,
            }
        )
        logger.debug(f"Answer to question with error: {output}")
        return output

    def answer_question_numeric(self, question: str, previous_questions: list[str]) -> str:
        """Answer numeric question"""
        current_date = datetime.now().date().strftime("%Y-%m-%d")

        chain = self.chains["numeric_question"]
        output = chain.invoke(
            {
                "resume": self.resume_readable,
                "question": question,
                "current_date": current_date,
                "previous_questions": previous_questions,
            }
        )
        logger.debug(f"Raw output for numeric question: {output}")
        if output.lower() == "no info":
            return output
        output = self._extract_number_from_string(output)
        logger.info(f"Extracted number: {output}")
        return output

    def _extract_number_from_string(self, output_str: str) -> str:
        """Extract number from string"""
        numbers = re.findall(r"\d+", output_str)
        if numbers:
            return str(numbers[0])
        else:
            logger.error("No numbers found in the string")
            raise ValueError("No numbers found in the string")

    def select_one_answer_from_options(
        self, question: str, options: list[str], previous_questions: list[str]
    ) -> str:
        """
        Ask LLM a question with one answer option.
        Return the best option.
        """
        gender = self.resume_structured["personal_information"]["gender"]
        func_template = self._preprocess_template_string(prompts.options_template)
        prompt = ChatPromptTemplate.from_template(func_template)
        chain = prompt | self.llm_cheap | StrOutputParser()
        output_str = chain.invoke(
            {
                "resume": self.resume_readable,
                "question": question,
                "options": options,
                "gender": gender,
                "previous_questions": previous_questions,
            }
        )
        logger.debug(f"LLM response: {output_str}")
        best_option = self.find_best_match(output_str, options)
        if best_option.lower() != "no info":
            logger.info(f"Best option found: {best_option}")
        return best_option

    def select_many_answers_from_options(
        self, question: str, options: list[str], previous_questions: list[str]
    ) -> List[str]:
        """
        Ask LLM a question with one or more answer options.
        Return a list of best options.
        """
        logger.info(f"Asking question: {question}")
        logger.info(f"Available options: {options}")
        gender = self.resume_structured["personal_information"]["gender"]
        func_template = self._preprocess_template_string(prompts.many_options_template)
        prompt = ChatPromptTemplate.from_template(func_template)
        chain = prompt | self.llm_cheap | StrOutputParser()
        output_str = chain.invoke(
            {
                "resume": self.resume_readable,
                "question": question,
                "options": options,
                "gender": gender,
                "previous_questions": previous_questions,
            }
        )
        logger.debug(f"LLM response: {output_str}")
        # in case LLM returns a python-like list
        output_str = output_str.replace("[", "").replace("]", "")
        output_str = output_str.replace("'", "").replace("'", "")
        outputs = output_str.split(";")
        best_options = []
        for output in outputs:
            best_option = self.find_best_match(output, options)
            best_options.append(best_option)
        logger.info(f"Best options: {best_options}")
        return best_options

    def job_is_interesting(self, job: Dict[str, Any]) -> bool | None:
        """
        Ask LLM if the job is interesting with our resume, skills and interests.
        Return True if the job is interesting, False otherwise.
        """
        chain = self.chains["job_is_interesting"]
        job_description = transform_vacancy_data(job)
        try:
            output = chain.invoke(
                {
                    "resume": self.resume_readable,
                    "job_description": job_description,
                    "search_parameters": self.search_parameters,
                }
            )
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Error calling LLM\n{tb_str}")
            return None
        logger.debug(f"LLM response: '{output}'")
        # parse the LLM response
        try:
            score = re.search(r"Score: (\d+)", output).group(1)
            reasoning = re.search(r"Reasoning: (.+)", output, re.DOTALL).group(1)
        except AttributeError:
            logger.error(f"LLM returned an incorrect response:\n{output}")
            return False
        logger.info(f"Job interest score: {score}")
        if int(score) < JOB_IS_INTERESTING_THRESH:
            logger.info(f"Job is not interesting: {reasoning}")
            return False, score, reasoning
        return True, score, reasoning

    def write_cover_letter(self) -> str:
        """
        Create a cover letter based on the resume and job description.
        Return the text of the cover letter.
        """
        # depending on the availability of the contact, set it in the prompt
        logger.info("Writing cover letter")
        phone = self.resume_structured["personal_information"].get("phone", "")
        phone_code = self.resume_structured["personal_information"].get("phone_code", "")
        email = self.resume_structured["personal_information"].get("email", "")
        additional_prompt = "- Specify the following contacts: "
        invoke_dict = {
            "resume": self.resume_readable,
            "company_name": self.job["company_name"],
            "job_description": self.job_readable,
        }
        if phone:
            additional_prompt += f"Phone: {phone_code} {phone}\n"
            invoke_dict["phone"] = f"{phone_code} {phone}"
        if email:
            additional_prompt += f"Email: {email}\n"
            invoke_dict["email"] = email

        chain = self.chains["prompt_cover_letter"]
        output = chain.invoke(invoke_dict)
        logger.debug(f"Cover letter generated: {output}")
        return output

    def resume_improvement_recommendations(self) -> str:
        """
        Write resume improvement recommendations
        """
        logger.info("Writing resume improvement recommendations")
        chain = self.chains["resume_improvement"]
        output = chain.invoke(
            {
                "resume": self.resume_readable,
            }
        )
        logger.debug(f"Resume improvement recommendations generated: {output}")
        return output

    def generate_header(self) -> str:
        """Generating resume header"""
        logger.info("Generating resume header")
        chain = self.chains["prompt_header"]

        output = chain.invoke(
            {
                "personal_information": self.resume_structured["personal_information"],
            }
        )
        logger.debug(f"Header generated: {output}")
        cleaned_output = self._clean_html_response(output)
        logger.info("Resume header generated")
        return cleaned_output

    def generate_education_section(self) -> str:
        """Generating education section for resume"""
        logger.info("Generating education section for resume")
        chain = self.chains["prompt_education"]
        output = chain.invoke(
            {
                "education_details": self.resume_structured["education_details"],
                "job_description": self.job_readable,
            }
        )
        logger.debug(f"Education section generated: {output}")
        cleaned_output = self._clean_html_response(output)
        logger.info("Education section generated")
        return cleaned_output

    def generate_work_experience_section(self) -> str:
        """Generating work experience section for resume"""
        logger.info("Generating work experience section for resume")
        chain = self.chains["prompt_working_experience"]
        output = chain.invoke(
            {
                "experience_details": self.resume_structured["experience_details"],
                "job_description": self.job_readable,
            }
        )
        logger.debug(f"Work experience section generated: {output}")
        cleaned_output = self._clean_html_response(output)
        logger.info("Work experience section generated")
        return cleaned_output

    def generate_side_projects_section(self) -> str:
        """Generating side projects section for resume"""
        logger.info("Generating side projects section for resume")
        chain = self.chains["prompt_side_projects"]
        output = chain.invoke(
            {
                "projects": self.resume_structured["projects"],
                "job_description": self.job_readable,
            }
        )
        logger.debug(f"Side projects section generated: {output}")
        cleaned_output = self._clean_html_response(output)
        logger.info("Side projects section generated")
        return cleaned_output

    def generate_achievements_section(self) -> str:
        """Generating achievements section for resume"""
        logger.info("Generating achievements section for resume")
        chain = self.chains["prompt_achievements"]
        input_data = {
            "achievements": self.resume_structured["achievements"],
            "job_description": self.job_readable,
        }

        output = chain.invoke(input_data)
        logger.debug(f"Achievements section generated: {output}")
        cleaned_output = self._clean_html_response(output)
        logger.info("Achievements section generated")
        return cleaned_output

    def generate_certifications_section(self) -> str:
        """Generate certifications section for resume"""
        logger.info("Generating certifications section for resume")
        chain = self.chains["prompt_certifications"]
        input_data = {
            "certifications": self.resume_structured["certifications"],
            "job_description": self.job_readable,
        }

        output = chain.invoke(input_data)
        logger.debug(f"Certifications section generated: {output}")
        cleaned_output = self._clean_html_response(output)
        logger.info("Certifications section generated")
        return cleaned_output

    def generate_additional_skills_section(self) -> str:
        """Generate skills section for resume"""
        logger.info("Generating additional skills section for resume")

        chain = self.chains["prompt_additional_skills"]
        output = chain.invoke(
            {
                "languages": self.resume_structured["languages"],
                "skills": self.resume_structured["skills"],
                "interests": self.resume_structured["interests"],
                "job_description": self.job_readable,
            }
        )
        logger.debug(f"Additional skills section generated: {output}")
        cleaned_output = self._clean_html_response(output)
        logger.info("Additional skills section generated")
        return cleaned_output

    def generate_html_resume(self) -> str:
        """Creating a resume from generated components"""

        def header_fn():
            template_resume = self.load_resume_template("header")
            if template_resume:
                return template_resume
            if self.resume_structured["personal_information"] and self.job_readable:
                header = self.generate_header()
                self.save_resume_template("header", header)
                return header
            return ""

        def education_fn():
            if self.resume_structured["education_details"] and self.job_readable:
                return self.generate_education_section()
            return ""

        def work_experience_fn():
            if self.resume_structured["experience_details"] and self.job_readable:
                return self.generate_work_experience_section()
            return ""

        def side_projects_fn():
            if self.resume_structured["projects"] and self.job_readable:
                return self.generate_side_projects_section()
            return ""

        def achievements_fn():
            if self.resume_structured["achievements"] and self.job_readable:
                return self.generate_achievements_section()
            return ""

        def certifications_fn():
            if self.resume_structured["certifications"] and self.job_readable:
                return self.generate_certifications_section()
            return ""

        def additional_skills_fn():
            if (
                self.resume_structured["experience_details"]
                or self.resume_structured["education_details"]
                or self.resume_structured["languages"]
                or self.resume_structured["interests"]
                or self.resume_structured["skills"]
                or self.resume_structured["about_me"]
            ) and self.job_readable:
                return self.generate_additional_skills_section()
            return ""

        # Create a dictionary to map the function names to their respective callables
        functions = {
            "header": header_fn,
            "education": education_fn,
            "work_experience": work_experience_fn,
            "side_projects": side_projects_fn,
            "achievements": achievements_fn,
            "certifications": certifications_fn,
            "additional_skills": additional_skills_fn,
        }

        # Use ThreadPoolExecutor to run the functions in parallel
        with ThreadPoolExecutor() as executor:
            future_to_section = {executor.submit(fn): section for section, fn in functions.items()}
            results = {}
            for future in as_completed(future_to_section):
                section = future_to_section[future]
                try:
                    result = future.result()
                    if result:
                        results[section] = result
                except Exception:
                    tb_str = traceback.format_exc()
                    logger.error(f"Section {section} processed with an error\n{tb_str}")
        full_resume = "<body>\n"
        full_resume += f"  {results.get('header', '')}\n"
        full_resume += "  <main>\n"
        full_resume += f"    {results.get('education', '')}\n"
        full_resume += f"    {results.get('work_experience', '')}\n"
        full_resume += f"    {results.get('side_projects', '')}\n"
        full_resume += f"    {results.get('achievements', '')}\n"
        full_resume += f"    {results.get('certifications', '')}\n"
        full_resume += f"    {results.get('additional_skills', '')}\n"
        full_resume += "  </main>\n"
        full_resume += "</body>"
        return full_resume

    def load_resume_template(self, template_name: str) -> str:
        """Load template resume"""
        if not self.resume_template_dir.exists():
            self.resume_template_dir.mkdir(parents=True)
        try:
            with open(
                self.resume_template_dir / f"{template_name}.html", "r", encoding="utf-8"
            ) as f:
                resume_template = f.read()
                return resume_template
        except FileNotFoundError:
            return ""

    def save_resume_template(self, template_name: str, resume_template: str) -> None:
        """Save template resume"""
        with open(self.resume_template_dir / f"{template_name}.html", "w", encoding="utf-8") as f:
            f.write(resume_template)


if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("llm_api_key", "")
    llm_proxy = os.getenv("llm_proxy", "")
    llm_api_url = os.getenv("llm_api_url", None)

    adapter = AIAdapter(api_key, llm_proxy, llm_api_url)
    prompt = ChatPromptTemplate.from_messages(
        [("human", "Say 'model works correctly' and nothing else.")]
    ).format_prompt()
    response = adapter.invoke(prompt)
    print(f"Model response: {response.content}")
