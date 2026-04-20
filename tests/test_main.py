"""Test suite for main.py"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock problematic imports before importing main
sys.modules["browser_use"] = MagicMock()
sys.modules["browser_use.tools"] = MagicMock()
sys.modules["browser_use.tools.views"] = MagicMock()

from main import ConfigError, ConfigValidator, create_and_run_bot, main


class TestConfigValidator:
    """Tests for ConfigValidator class"""

    def test_validate_search_config_success(self, tmp_path):
        """Test successful validation of search config"""
        config_file = tmp_path / "search_config.yaml"
        config_data = {
            "remote": True,
            "hybrid": False,
            "onsite": False,
            "experience_level": {"mid_senior_level": True},
            "job_types": {"full_time": True},
            "positions": ["Software Engineer"],
            "locations": ["New York"],
            "apply_once_at_company": True,
            "company_blacklist": [],
        }

        # Mock load_yaml_file
        with patch("main.load_yaml_file", return_value=config_data):
            validator = ConfigValidator()
            result = validator.validate_search_config(config_file)

            # Check key fields are present (Pydantic adds defaults)
            assert result["positions"] == ["Software Engineer"]
            assert result["remote"] is True
            assert result["hybrid"] is False
            assert result["onsite"] is False
            assert result["locations"] == ["New York"]
            assert result["apply_once_at_company"] is True
            assert "experience_level" in result
            assert "job_types" in result

    def test_validate_search_config_missing_required_fields(self, tmp_path):
        """Test validation fails with missing required fields"""
        config_file = tmp_path / "invalid_config.yaml"
        invalid_data = {"remote": True}  # Missing required fields

        with patch("main.load_yaml_file", return_value=invalid_data):
            validator = ConfigValidator()

            with pytest.raises(ConfigError, match="LinkedIn configuration validation error"):
                validator.validate_search_config(config_file)

    def test_validate_search_config_load_error(self, tmp_path):
        """Test validation fails when file cannot be loaded"""
        config_file = tmp_path / "missing.yaml"

        with patch("main.load_yaml_file", side_effect=FileNotFoundError("File not found")):
            validator = ConfigValidator()

            with pytest.raises(ConfigError, match="LinkedIn configuration validation error"):
                validator.validate_search_config(config_file)

    def test_validate_secrets_success(self):
        """Test successful validation of secrets"""
        mock_secrets = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "securepass123",
            "llm_api_key": "api_key_123",
            "llm_proxy": "",
            "tg_token": "telegram_token_123",
        }

        with patch("dotenv.dotenv_values", return_value=mock_secrets):
            validator = ConfigValidator()
            result = validator.validate_secrets()

            assert result["linkedin_email"] == "test@example.com"
            assert result["linkedin_password"] == "securepass123"
            assert result["tg_token"] == "telegram_token_123"

    def test_validate_secrets_missing_linkedin_email(self):
        """Test validation fails when linkedin_email is missing"""
        mock_secrets = {
            "linkedin_password": "securepass123",
        }

        with patch("dotenv.dotenv_values", return_value=mock_secrets):
            validator = ConfigValidator()

            with pytest.raises(ConfigError, match="Missing required keys: linkedin_email"):
                validator.validate_secrets()

    def test_validate_secrets_missing_linkedin_password(self):
        """Test validation fails when linkedin_password is missing"""
        mock_secrets = {
            "linkedin_email": "test@example.com",
        }

        with patch("dotenv.dotenv_values", return_value=mock_secrets):
            validator = ConfigValidator()

            with pytest.raises(ConfigError, match="Missing required keys: linkedin_password"):
                validator.validate_secrets()

    def test_validate_secrets_missing_multiple_keys(self):
        """Test validation fails when multiple required keys are missing"""
        mock_secrets = {}

        with patch("dotenv.dotenv_values", return_value=mock_secrets):
            validator = ConfigValidator()

            with pytest.raises(
                ConfigError, match="Missing required keys: linkedin_email, linkedin_password"
            ):
                validator.validate_secrets()

    def test_validate_secrets_empty_values(self):
        """Test validation fails when required values are empty"""
        mock_secrets = {
            "linkedin_email": "",
            "linkedin_password": "securepass123",
        }

        with patch("dotenv.dotenv_values", return_value=mock_secrets):
            validator = ConfigValidator()

            with pytest.raises(ConfigError, match="Missing required keys: linkedin_email"):
                validator.validate_secrets()

    def test_validate_resume_text_success(self, tmp_path):
        """Test successful validation of resume text"""
        resume_file = tmp_path / "resume.txt"
        resume_content = "John Doe\nSoftware Engineer\nExperience: 5 years"

        with open(resume_file, "w", encoding="utf-8") as f:
            f.write(resume_content)

        validator = ConfigValidator()
        result = validator.validate_resume_text(resume_file)

        assert result == resume_content

    def test_validate_resume_text_empty_file(self, tmp_path):
        """Test validation fails when resume file is empty"""
        resume_file = tmp_path / "empty_resume.txt"
        resume_file.write_text("")

        validator = ConfigValidator()

        with pytest.raises(ConfigError, match="Resume not found"):
            validator.validate_resume_text(resume_file)

    def test_validate_resume_text_file_not_found(self, tmp_path):
        """Test validation returns empty string when file doesn't exist"""
        resume_file = tmp_path / "nonexistent.txt"

        validator = ConfigValidator()
        result = validator.validate_resume_text(resume_file)

        assert result == ""

    def test_validate_resume_text_read_error(self, tmp_path):
        """Test validation fails on read error"""
        resume_file = tmp_path / "resume.txt"
        resume_file.write_text("content")

        validator = ConfigValidator()

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(ConfigError, match="Resume validation error"):
                validator.validate_resume_text(resume_file)

    def test_validate_resume_structured_success(self, tmp_path):
        """Test successful validation of structured resume"""
        resume_data = {
            "personal_information": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "1234567890",
                "gender": "Male",
            },
            "self_identification": {
                "gender": "Male",
                "pronouns": "He/Him",
                "veteran": "No",
                "disability": "No",
                "ethnicity": "No info",
            },
            "legal_authorization": {
                "eu_work_authorization": "Yes",
                "us_work_authorization": "No",
                "requires_us_visa": "No",
                "requires_us_sponsorship": "No",
                "requires_eu_visa": "No",
                "legally_allowed_to_work_in_eu": "Yes",
                "legally_allowed_to_work_in_us": "No",
            },
            "work_preferences": {
                "remote_work": "Yes",
                "in_person_work": "No",
                "open_to_relocation": "No",
                "willing_to_complete_assessments": "Yes",
                "willing_to_undergo_drug_tests": "No",
                "willing_to_undergo_background_checks": "Yes",
            },
            "education_details": [],
            "experience_details": [],
            "projects": [],
            "availability": {"notice_period": "2 weeks"},
            "salary_expectations": {"salary_range_usd": "100000-150000"},
            "certifications": [],
            "languages": [{"language": "English", "proficiency": "Native"}],
            "interests": [],
        }

        with patch("main.load_yaml_file", return_value=resume_data):
            validator = ConfigValidator()
            result = validator.validate_resume_structured(tmp_path / "resume.yaml")

            assert result["personal_information"]["first_name"] == "John"
            assert result["personal_information"]["last_name"] == "Doe"

    def test_validate_resume_structured_missing_fields(self, tmp_path):
        """Test validation fails with missing required fields"""
        invalid_data = {"personal_information": {"name": "John"}}

        with patch("main.load_yaml_file", return_value=invalid_data):
            validator = ConfigValidator()

            with pytest.raises(ConfigError, match="Structured resume validation error"):
                validator.validate_resume_structured(tmp_path / "resume.yaml")

    def test_validate_resume_structured_file_not_found(self, tmp_path):
        """Test validation returns empty dict when file not found"""
        with patch("main.load_yaml_file", side_effect=Exception("File not found: test.yaml")):
            validator = ConfigValidator()
            result = validator.validate_resume_structured(tmp_path / "resume.yaml")

            assert result == {}

    def test_validate_resume_structured_other_error(self, tmp_path):
        """Test validation fails on other errors"""
        with patch("main.load_yaml_file", side_effect=Exception("YAML parse error")):
            validator = ConfigValidator()

            with pytest.raises(ConfigError, match="Structured resume validation error"):
                validator.validate_resume_structured(tmp_path / "resume.yaml")


class TestCreateAndRunBot:
    """Tests for create_and_run_bot async function"""

    @pytest.mark.asyncio
    async def test_create_and_run_bot_browser_initialization_error(self):
        """Test bot creation fails when browser initialization errors"""
        with patch(
            "main.create_playwright_browser",
            new_callable=AsyncMock,
            side_effect=Exception("Browser init failed"),
        ):
            with pytest.raises(RuntimeError, match="Failed to initialize browser"):
                await create_and_run_bot({}, {}, "", {})

    @pytest.mark.asyncio
    async def test_create_and_run_bot_login_failure(self):
        """Test bot returns False when login fails"""
        # Mock browser components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock authenticator
        mock_authenticator = AsyncMock()
        mock_authenticator.start = AsyncMock(return_value=False)

        search_config = {"positions": ["Software Engineer"], "locations": ["Remote"]}
        secrets = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "password",
            "llm_api_key": "api_key",
            "llm_proxy": "",
        }

        with (
            patch(
                "main.create_playwright_browser",
                new_callable=AsyncMock,
                return_value=(mock_browser, mock_context, mock_page),
            ),
            patch("main.save_browser_session", new_callable=AsyncMock),
            patch("main.LinkedInAuthenticator", return_value=mock_authenticator),
        ):
            result = await create_and_run_bot(search_config, secrets, "", {})

            assert result is False
            mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_and_run_bot_success_with_existing_resume(self):
        """Test successful bot execution with existing structured resume"""
        # Mock browser components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock authenticator
        mock_authenticator = AsyncMock()
        mock_authenticator.start = AsyncMock(return_value=True)

        # Mock components
        mock_gpt_answerer = MagicMock()
        mock_apply_agent = MagicMock()
        mock_resume_anonymizer = MagicMock()
        mock_resume_anonymizer.resume_anonymized = {}
        mock_resume_anonymizer.anonymize_text = MagicMock(return_value="anonymized text")
        mock_style_manager = MagicMock()
        mock_resume_generator = MagicMock()
        mock_resume_manager = MagicMock()
        mock_search_component = MagicMock()
        mock_apply_component = MagicMock()
        mock_apply_component.check_the_last_search_time = MagicMock(return_value=True)
        mock_bot_facade = AsyncMock()

        search_config = {"positions": ["Software Engineer"], "locations": ["Remote"]}
        secrets = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "password",
            "llm_api_key": "api_key",
            "llm_proxy": "",
        }
        resume_text = "John Doe Resume"
        resume_structured = {
            "personal_information": {
                "name": "John",
                "surname": "Doe",
                "email": "john@example.com",
                "phone": "1234567890",
            },
            "self_identification": {
                "gender": "Male",
                "pronouns": "He/Him",
                "veteran": False,
                "disability": False,
            },
            "legal_authorization": {
                "eu_work_authorization": True,
                "us_work_authorization": False,
                "requires_us_visa": False,
                "requires_us_sponsorship": False,
            },
            "work_preferences": {
                "remote_work": True,
                "in_person_work": False,
                "open_to_relocation": False,
                "willing_to_complete_assessments": True,
            },
            "education_details": [],
            "experience_details": [],
            "projects": [],
            "availability": {"notice_period": "2 weeks"},
            "salary_expectations": {"salary_range_usd": "100000-150000"},
            "certifications": [],
            "languages": [{"language": "English", "proficiency": "Native"}],
            "interests": [],
        }

        # Create mock for READY_MADE_RESUME path
        mock_resume_file = MagicMock()
        mock_resume_file.resolve.return_value.is_file.return_value = True

        with (
            patch(
                "main.create_playwright_browser",
                new_callable=AsyncMock,
                return_value=(mock_browser, mock_context, mock_page),
            ),
            patch("main.save_browser_session", new_callable=AsyncMock),
            patch("main.LinkedInAuthenticator", return_value=mock_authenticator),
            patch("main.GPTAnswerer", return_value=mock_gpt_answerer),
            patch("main.ApplyAgent", return_value=mock_apply_agent),
            patch("main.ResumeAnonymizer", return_value=mock_resume_anonymizer),
            patch("main.StyleManager", return_value=mock_style_manager),
            patch("main.ResumeGenerator", return_value=mock_resume_generator),
            patch("main.ResumeManager", return_value=mock_resume_manager),
            patch("main.SearchCustomizer", return_value=mock_search_component),
            patch("main.JobApplier", return_value=mock_apply_component),
            patch("main.BotFacade", return_value=mock_bot_facade),
            patch("main.validate_and_prompt_resume_completion", return_value=True),
            patch("main.READY_MADE_RESUME", mock_resume_file),
        ):
            await create_and_run_bot(search_config, secrets, resume_text, resume_structured)

            # Verify login was attempted
            mock_authenticator.start.assert_called_once()

            # Verify bot facade was initialized and started
            mock_bot_facade.set_parameters.assert_called_once()
            mock_bot_facade.set_answerer_and_agent.assert_called_once()
            mock_bot_facade.set_resume.assert_called_once()
            mock_bot_facade.start_apply.assert_called_once()

            # Verify browser cleanup
            mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_and_run_bot_parses_resume_when_not_structured(self):
        """Test bot parses resume when structured resume is not provided"""
        # Mock browser components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock authenticator
        mock_authenticator = AsyncMock()
        mock_authenticator.start = AsyncMock(return_value=True)

        # Mock GPT answerer with parse_resume
        mock_gpt_answerer = MagicMock()
        parsed_resume = {
            "personal_information": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "1234567890",
                "gender": "Male",
            },
            "self_identification": {
                "gender": "Male",
                "pronouns": "He/Him",
                "veteran": "No",
                "disability": "No",
                "ethnicity": "No info",
            },
            "legal_authorization": {
                "eu_work_authorization": "Yes",
                "us_work_authorization": "No",
                "requires_us_visa": "No",
                "requires_us_sponsorship": "No",
                "requires_eu_visa": "No",
                "legally_allowed_to_work_in_eu": "Yes",
                "legally_allowed_to_work_in_us": "No",
            },
            "work_preferences": {
                "remote_work": "Yes",
                "in_person_work": "No",
                "open_to_relocation": "No",
                "willing_to_complete_assessments": "Yes",
                "willing_to_undergo_drug_tests": "No",
                "willing_to_undergo_background_checks": "Yes",
            },
            "education_details": [],
            "experience_details": [],
            "projects": [],
            "availability": {"notice_period": "2 weeks"},
            "salary_expectations": {"salary_range_usd": "100000-150000"},
            "certifications": [],
            "languages": [{"language": "English", "proficiency": "Native"}],
            "interests": [],
        }
        mock_gpt_answerer.parse_resume = MagicMock(return_value=parsed_resume)

        # Mock other components
        mock_apply_agent = MagicMock()
        mock_resume_anonymizer = MagicMock()
        mock_resume_anonymizer.resume_anonymized = parsed_resume
        mock_resume_anonymizer.anonymize_text = MagicMock(return_value="anonymized text")
        mock_style_manager = MagicMock()
        mock_resume_generator = MagicMock()
        mock_resume_manager = MagicMock()
        mock_search_component = MagicMock()
        mock_apply_component = MagicMock()
        mock_apply_component.check_the_last_search_time = MagicMock(return_value=True)
        mock_bot_facade = AsyncMock()

        search_config = {"positions": ["Software Engineer"]}
        secrets = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "password",
            "llm_api_key": "api_key",
            "llm_proxy": "",
        }
        resume_text = "John Doe Resume"
        resume_structured = {}  # Empty - needs parsing

        # Create mock for READY_MADE_RESUME path
        mock_resume_file = MagicMock()
        mock_resume_file.resolve.return_value.is_file.return_value = True

        with (
            patch(
                "main.create_playwright_browser",
                new_callable=AsyncMock,
                return_value=(mock_browser, mock_context, mock_page),
            ),
            patch("main.save_browser_session", new_callable=AsyncMock),
            patch("main.LinkedInAuthenticator", return_value=mock_authenticator),
            patch("main.GPTAnswerer", return_value=mock_gpt_answerer),
            patch("main.ApplyAgent", return_value=mock_apply_agent),
            patch("main.ResumeAnonymizer", return_value=mock_resume_anonymizer),
            patch("main.StyleManager", return_value=mock_style_manager),
            patch("main.ResumeGenerator", return_value=mock_resume_generator),
            patch("main.ResumeManager", return_value=mock_resume_manager),
            patch("main.SearchCustomizer", return_value=mock_search_component),
            patch("main.JobApplier", return_value=mock_apply_component),
            patch("main.BotFacade", return_value=mock_bot_facade),
            patch("main.save_yaml_file") as mock_save_yaml,
            patch("main.validate_and_prompt_resume_completion", return_value=True),
            patch("main.READY_MADE_RESUME", mock_resume_file),
        ):
            await create_and_run_bot(search_config, secrets, resume_text, resume_structured)

            # Verify resume was parsed
            mock_gpt_answerer.parse_resume.assert_called_once_with(resume_text)

            # Verify parsed resume was saved
            mock_save_yaml.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_and_run_bot_last_search_too_recent(self):
        """Test bot exits early when last search was too recent"""
        # Mock browser components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock authenticator
        mock_authenticator = AsyncMock()
        mock_authenticator.start = AsyncMock(return_value=True)

        # Mock components
        mock_gpt_answerer = MagicMock()
        mock_apply_agent = MagicMock()
        mock_resume_anonymizer = MagicMock()
        mock_resume_anonymizer.resume_anonymized = {}
        mock_resume_anonymizer.anonymize_text = MagicMock(return_value="anonymized text")
        mock_search_component = MagicMock()
        mock_apply_component = MagicMock()
        mock_apply_component.check_the_last_search_time = MagicMock(
            return_value=False
        )  # Last search too recent
        mock_bot_facade = AsyncMock()

        search_config = {"positions": ["Software Engineer"]}
        secrets = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "password",
            "llm_api_key": "api_key",
            "llm_proxy": "",
        }
        resume_structured = {
            "personal_information": {
                "name": "John",
                "surname": "Doe",
                "email": "john@example.com",
                "phone": "1234567890",
            },
            "self_identification": {
                "gender": "Male",
                "pronouns": "He/Him",
                "veteran": False,
                "disability": False,
            },
            "legal_authorization": {
                "eu_work_authorization": True,
                "us_work_authorization": False,
                "requires_us_visa": False,
                "requires_us_sponsorship": False,
            },
            "work_preferences": {
                "remote_work": True,
                "in_person_work": False,
                "open_to_relocation": False,
                "willing_to_complete_assessments": True,
            },
            "education_details": [],
            "experience_details": [],
            "projects": [],
            "availability": {"notice_period": "2 weeks"},
            "salary_expectations": {"salary_range_usd": "100000-150000"},
            "certifications": [],
            "languages": [{"language": "English", "proficiency": "Native"}],
            "interests": [],
        }

        # Create mock for READY_MADE_RESUME path
        mock_resume_file = MagicMock()
        mock_resume_file.resolve.return_value.is_file.return_value = True

        with (
            patch(
                "main.create_playwright_browser",
                new_callable=AsyncMock,
                return_value=(mock_browser, mock_context, mock_page),
            ),
            patch("main.save_browser_session", new_callable=AsyncMock),
            patch("main.LinkedInAuthenticator", return_value=mock_authenticator),
            patch("main.GPTAnswerer", return_value=mock_gpt_answerer),
            patch("main.ApplyAgent", return_value=mock_apply_agent),
            patch("main.ResumeAnonymizer", return_value=mock_resume_anonymizer),
            patch("main.StyleManager"),
            patch("main.ResumeGenerator"),
            patch("main.ResumeManager"),
            patch("main.SearchCustomizer", return_value=mock_search_component),
            patch("main.JobApplier", return_value=mock_apply_component),
            patch("main.BotFacade", return_value=mock_bot_facade),
            patch("main.READY_MADE_RESUME", mock_resume_file),
            patch("main.RESTART_EVERY_DAY", True),
        ):
            result = await create_and_run_bot(search_config, secrets, "", resume_structured)

            # Verify bot did not start applying
            mock_bot_facade.start_apply.assert_not_called()

            # Verify function returned True (completed, but didn't run)
            assert result is True

    @pytest.mark.asyncio
    async def test_create_and_run_bot_user_cancels_resume_completion(self):
        """Test bot exits when user cancels resume completion"""
        # Mock browser components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock authenticator
        mock_authenticator = AsyncMock()
        mock_authenticator.start = AsyncMock(return_value=True)

        # Mock components
        mock_gpt_answerer = MagicMock()
        mock_apply_agent = MagicMock()
        mock_resume_anonymizer = MagicMock()
        mock_resume_anonymizer.resume_anonymized = {}
        mock_resume_anonymizer.anonymize_text = MagicMock(return_value="anonymized text")
        mock_search_component = MagicMock()
        mock_apply_component = MagicMock()
        mock_apply_component.check_the_last_search_time = MagicMock(return_value=True)
        mock_bot_facade = AsyncMock()

        search_config = {"positions": ["Software Engineer"]}
        secrets = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "password",
            "llm_api_key": "api_key",
            "llm_proxy": "",
        }
        resume_structured = {
            "personal_information": {
                "name": "John",
                "surname": "Doe",
                "email": "john@example.com",
                "phone": "1234567890",
            },
            "self_identification": {
                "gender": "Male",
                "pronouns": "He/Him",
                "veteran": False,
                "disability": False,
            },
            "legal_authorization": {
                "eu_work_authorization": True,
                "us_work_authorization": False,
                "requires_us_visa": False,
                "requires_us_sponsorship": False,
            },
            "work_preferences": {
                "remote_work": True,
                "in_person_work": False,
                "open_to_relocation": False,
                "willing_to_complete_assessments": True,
            },
            "education_details": [],
            "experience_details": [],
            "projects": [],
            "availability": {"notice_period": "2 weeks"},
            "salary_expectations": {"salary_range_usd": "100000-150000"},
            "certifications": [],
            "languages": [{"language": "English", "proficiency": "Native"}],
            "interests": [],
        }

        # Create mock for READY_MADE_RESUME path
        mock_resume_file = MagicMock()
        mock_resume_file.resolve.return_value.is_file.return_value = True

        with (
            patch(
                "main.create_playwright_browser",
                new_callable=AsyncMock,
                return_value=(mock_browser, mock_context, mock_page),
            ),
            patch("main.save_browser_session", new_callable=AsyncMock),
            patch("main.LinkedInAuthenticator", return_value=mock_authenticator),
            patch("main.GPTAnswerer", return_value=mock_gpt_answerer),
            patch("main.ApplyAgent", return_value=mock_apply_agent),
            patch("main.ResumeAnonymizer", return_value=mock_resume_anonymizer),
            patch("main.StyleManager"),
            patch("main.ResumeGenerator"),
            patch("main.ResumeManager"),
            patch("main.SearchCustomizer", return_value=mock_search_component),
            patch("main.JobApplier", return_value=mock_apply_component),
            patch("main.BotFacade", return_value=mock_bot_facade),
            patch("main.validate_and_prompt_resume_completion", return_value=False),
            patch("main.READY_MADE_RESUME", mock_resume_file),
        ):
            result = await create_and_run_bot(search_config, secrets, "", resume_structured)

            # Verify bot did not start applying
            mock_bot_facade.start_apply.assert_not_called()

            # Verify function returned False (user cancelled)
            assert result is False

    @pytest.mark.asyncio
    async def test_create_and_run_bot_generates_resume_when_not_exists(self):
        """Test bot generates resume when ready-made resume doesn't exist"""
        # Mock browser components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock authenticator
        mock_authenticator = AsyncMock()
        mock_authenticator.start = AsyncMock(return_value=True)

        # Mock components
        mock_gpt_answerer = MagicMock()
        mock_apply_agent = MagicMock()
        mock_resume_anonymizer = MagicMock()
        mock_resume_anonymizer.resume_anonymized = {}
        mock_resume_anonymizer.anonymize_text = MagicMock(return_value="anonymized text")
        mock_style_manager = MagicMock()
        mock_resume_generator = MagicMock()
        mock_resume_manager = MagicMock()
        mock_search_component = MagicMock()
        mock_apply_component = MagicMock()
        mock_apply_component.check_the_last_search_time = MagicMock(return_value=True)
        mock_bot_facade = AsyncMock()

        search_config = {"positions": ["Software Engineer"]}
        secrets = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "password",
            "llm_api_key": "api_key",
            "llm_proxy": "",
        }
        resume_structured = {
            "personal_information": {
                "name": "John",
                "surname": "Doe",
                "email": "john@example.com",
                "phone": "1234567890",
            },
            "self_identification": {
                "gender": "Male",
                "pronouns": "He/Him",
                "veteran": False,
                "disability": False,
            },
            "legal_authorization": {
                "eu_work_authorization": True,
                "us_work_authorization": False,
                "requires_us_visa": False,
                "requires_us_sponsorship": False,
            },
            "work_preferences": {
                "remote_work": True,
                "in_person_work": False,
                "open_to_relocation": False,
                "willing_to_complete_assessments": True,
            },
            "education_details": [],
            "experience_details": [],
            "projects": [],
            "availability": {"notice_period": "2 weeks"},
            "salary_expectations": {"salary_range_usd": "100000-150000"},
            "certifications": [],
            "languages": [{"language": "English", "proficiency": "Native"}],
            "interests": [],
        }

        # Create mock for READY_MADE_RESUME path (file doesn't exist)
        mock_resume_file = MagicMock()
        mock_resume_file.resolve.return_value.is_file.return_value = False

        with (
            patch(
                "main.create_playwright_browser",
                new_callable=AsyncMock,
                return_value=(mock_browser, mock_context, mock_page),
            ),
            patch("main.save_browser_session", new_callable=AsyncMock),
            patch("main.LinkedInAuthenticator", return_value=mock_authenticator),
            patch("main.GPTAnswerer", return_value=mock_gpt_answerer),
            patch("main.ApplyAgent", return_value=mock_apply_agent),
            patch("main.ResumeAnonymizer", return_value=mock_resume_anonymizer),
            patch("main.StyleManager", return_value=mock_style_manager),
            patch("main.ResumeGenerator", return_value=mock_resume_generator),
            patch("main.ResumeManager", return_value=mock_resume_manager),
            patch("main.SearchCustomizer", return_value=mock_search_component),
            patch("main.JobApplier", return_value=mock_apply_component),
            patch("main.BotFacade", return_value=mock_bot_facade),
            patch("main.validate_and_prompt_resume_completion", return_value=True),
            patch("main.READY_MADE_RESUME", mock_resume_file),
        ):
            await create_and_run_bot(search_config, secrets, "", resume_structured)

            # Verify style was chosen
            mock_resume_manager.choose_style.assert_called_once()

            # Verify resume generator was set in bot
            mock_bot_facade.set_resume_generator.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_and_run_bot_cleanup_on_exception(self):
        """Test browser cleanup occurs even when exception is raised"""
        # Mock browser components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Mock authenticator that raises exception after login
        mock_authenticator = AsyncMock()
        mock_authenticator.start = AsyncMock(return_value=True)

        # Mock GPTAnswerer that raises exception
        mock_gpt_answerer = MagicMock()
        mock_gpt_answerer.parse_resume = MagicMock(side_effect=Exception("GPT API error"))

        search_config = {"positions": ["Software Engineer"]}
        secrets = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "password",
            "llm_api_key": "api_key",
            "llm_proxy": "",
        }

        with (
            patch(
                "main.create_playwright_browser",
                new_callable=AsyncMock,
                return_value=(mock_browser, mock_context, mock_page),
            ),
            patch("main.save_browser_session", new_callable=AsyncMock),
            patch("main.LinkedInAuthenticator", return_value=mock_authenticator),
            patch("main.GPTAnswerer", return_value=mock_gpt_answerer),
            patch("main.ApplyAgent"),
        ):
            with pytest.raises(Exception, match="GPT API error"):
                await create_and_run_bot(search_config, secrets, "", {})

            # Verify browser was closed even though exception occurred
            mock_browser.close.assert_called_once()


class TestMain:
    """Tests for main function"""

    def test_main_success(self):
        """Test successful execution of main function"""
        # Mock config validator
        mock_validator = MagicMock()
        mock_validator.validate_secrets.return_value = {
            "linkedin_email": "test@example.com",
            "linkedin_password": "password",
            "llm_api_key": "api_key",
            "llm_proxy": "",
        }
        mock_validator.validate_search_config.return_value = {"positions": ["Software Engineer"]}
        mock_validator.validate_resume_text.return_value = "Resume text"
        mock_validator.validate_resume_structured.return_value = {
            "personal_information": {"name": "John"}
        }

        with (
            patch("main.Path") as mock_path_class,
            patch("main.ConfigValidator", return_value=mock_validator),
            patch("main.asyncio.run") as mock_asyncio_run,
        ):
            # Setup mock Path
            mock_data = MagicMock()
            mock_output = MagicMock()
            mock_data.__truediv__.return_value = mock_output
            mock_path_class.return_value = mock_data

            main()

            # Verify output folder creation
            mock_output.mkdir.assert_called_once_with(exist_ok=True)

            # Verify config validation
            mock_validator.validate_secrets.assert_called_once()
            mock_validator.validate_search_config.assert_called_once()
            mock_validator.validate_resume_text.assert_called_once()
            mock_validator.validate_resume_structured.assert_called_once()

            # Verify bot was run
            mock_asyncio_run.assert_called_once()

    def test_main_config_error(self):
        """Test main handles ConfigError properly"""
        mock_validator = MagicMock()
        mock_validator.validate_secrets.side_effect = ConfigError("Missing secrets")

        with (
            patch("main.Path"),
            patch("main.ConfigValidator", return_value=mock_validator),
            patch("main.logger") as mock_logger,
        ):
            main()

            # Verify error was logged
            mock_logger.error.assert_any_call("Configuration error: Missing secrets")

    def test_main_file_not_found(self):
        """Test main handles FileNotFoundError properly"""
        mock_validator = MagicMock()
        mock_validator.validate_secrets.return_value = {}
        mock_validator.validate_search_config.side_effect = FileNotFoundError("Config not found")

        with (
            patch("main.Path"),
            patch("main.ConfigValidator", return_value=mock_validator),
            patch("main.logger") as mock_logger,
        ):
            main()

            # Verify error was logged with traceback
            assert any("File not found" in str(call) for call in mock_logger.error.call_args_list)

    def test_main_runtime_error(self):
        """Test main handles RuntimeError properly"""
        mock_validator = MagicMock()
        mock_validator.validate_secrets.return_value = {}
        mock_validator.validate_search_config.return_value = {}
        mock_validator.validate_resume_text.return_value = "resume text"
        mock_validator.validate_resume_structured.return_value = {}

        with (
            patch("main.Path"),
            patch("main.ConfigValidator", return_value=mock_validator),
            patch("main.asyncio.run", side_effect=RuntimeError("Browser failed")),
            patch("main.logger") as mock_logger,
        ):
            main()

            # Verify error was logged with traceback
            assert any("Runtime error" in str(call) for call in mock_logger.error.call_args_list)

    def test_main_unexpected_exception(self):
        """Test main handles unexpected exceptions properly"""
        mock_validator = MagicMock()
        mock_validator.validate_secrets.side_effect = ValueError("Unexpected error")

        with (
            patch("main.Path"),
            patch("main.ConfigValidator", return_value=mock_validator),
            patch("main.logger") as mock_logger,
        ):
            main()

            # Verify error was logged as unknown error
            assert any("Unknown error" in str(call) for call in mock_logger.error.call_args_list)

    def test_main_creates_output_folder(self):
        """Test main creates output folder if it doesn't exist"""
        mock_validator = MagicMock()
        mock_validator.validate_secrets.side_effect = ConfigError("Stop execution")

        mock_output = MagicMock()

        with (
            patch("main.Path") as mock_path_class,
            patch("main.ConfigValidator", return_value=mock_validator),
            patch("main.logger"),
        ):
            # Setup mock Path
            mock_data = MagicMock()
            mock_data.__truediv__.return_value = mock_output
            mock_path_class.return_value = mock_data

            main()

            # Verify mkdir was called with exist_ok=True
            mock_output.mkdir.assert_called_once_with(exist_ok=True)

    def test_main_logs_search_config_parameters(self):
        """Test main logs search config parameter count"""
        mock_validator = MagicMock()
        mock_validator.validate_secrets.return_value = {}
        search_config_data = {
            "positions": ["Software Engineer"],
            "locations": ["Remote"],
            "remote": True,
        }
        mock_validator.validate_search_config.return_value = search_config_data
        mock_validator.validate_resume_text.return_value = "resume"
        mock_validator.validate_resume_structured.return_value = {}

        with (
            patch("main.Path"),
            patch("main.ConfigValidator", return_value=mock_validator),
            patch("main.asyncio.run"),
            patch("main.logger") as mock_logger,
        ):
            main()

            # Verify parameter count was logged
            mock_logger.info.assert_any_call(
                f"Search config loaded with {len(search_config_data)} parameters"
            )

    def test_main_completion_logged(self):
        """Test main logs completion message"""
        mock_validator = MagicMock()
        mock_validator.validate_secrets.return_value = {}
        mock_validator.validate_search_config.return_value = {}
        mock_validator.validate_resume_text.return_value = "resume text"
        mock_validator.validate_resume_structured.return_value = {}

        with (
            patch("main.Path"),
            patch("main.ConfigValidator", return_value=mock_validator),
            patch("main.asyncio.run"),
            patch("main.logger") as mock_logger,
        ):
            main()

            # Verify completion messages
            mock_logger.info.assert_any_call("LinkedIn bot completed successfully")
            mock_logger.info.assert_any_call("Program completed")
