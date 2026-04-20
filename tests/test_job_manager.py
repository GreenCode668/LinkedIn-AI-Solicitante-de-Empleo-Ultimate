from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.job_manager.job_manager import JobApplier
from src.pydantic_models.job_models import Job, JobManagerCache

# yaml is intentionally not imported to avoid real file I/O in tests


@pytest.fixture
def mock_page():
    """Create a mock Playwright page object"""
    page = MagicMock()
    page.url = "https://linkedin.com/jobs/view/12345"
    return page


@pytest.fixture
def mock_resume_anonymizer():
    """Create a mock resume anonymizer"""
    anonymizer = MagicMock()
    anonymizer.deanonymize_text = lambda text: text
    return anonymizer


@pytest.fixture
def mock_search_component():
    """Create a mock search component"""
    return MagicMock()


@pytest.fixture
def mock_file_system():
    """Mock all file system operations to prevent actual file I/O"""
    with (
        patch("builtins.open", mock_open()) as mock_file,
        patch("yaml.safe_load") as mock_yaml_load,
        patch("yaml.dump") as mock_yaml_dump,
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.mkdir") as mock_mkdir,
    ):
        mock_yaml_load.return_value = {}
        mock_yaml_dump.return_value = ""
        mock_exists.return_value = False

        yield {
            "open": mock_file,
            "yaml_load": mock_yaml_load,
            "yaml_dump": mock_yaml_dump,
            "exists": mock_exists,
            "mkdir": mock_mkdir,
        }


@pytest.fixture
def job_applier(mock_page, mock_resume_anonymizer, mock_search_component):
    """Create a JobApplier instance for testing with mocked file operations"""
    with (
        patch("src.job_manager.job_manager.OUTPUT_DIR", "/mock/output"),
        patch("src.job_manager.job_manager.LAST_RUN_FILE", Path("/mock/output/last_run.yaml")),
        patch("builtins.open", mock_open()),
        patch("yaml.safe_load", return_value={}),
        patch("yaml.dump", return_value=""),
    ):
        applier = JobApplier(
            page=mock_page,
            linkedin_email="test@example.com",
            resume_anonymizer=mock_resume_anonymizer,
            search_component=mock_search_component,
        )
        return applier


class TestJobApplierInitialization:
    """Test JobApplier initialization"""

    def test_init_sets_basic_attributes(
        self, mock_page, mock_resume_anonymizer, mock_search_component
    ):
        """Test that __init__ sets all basic attributes correctly"""
        applier = JobApplier(
            page=mock_page,
            linkedin_email="test@example.com",
            resume_anonymizer=mock_resume_anonymizer,
            search_component=mock_search_component,
        )

        assert applier.page == mock_page
        assert applier.linkedin_email == "test@example.com"
        assert applier.resume_anonymizer == mock_resume_anonymizer
        assert applier.search_component == mock_search_component
        assert applier.llm_answerer_component is None
        assert applier.llm_agent_component is None
        assert applier.resume_generator_manager is None
        assert applier.jobs_no_info == []
        assert applier.job_key_skills == []
        assert applier.interesting_jobs == []
        assert applier.page_num == 0
        assert applier.resume_vac_page_num == -1
        assert applier.error_num == 0
        assert applier.total_applies_num == 0
        assert applier.resume_recommendations == ""


class TestSetters:
    """Test setter methods"""

    def test_set_answerer_and_agent(self, job_applier):
        """Test setting LLM answerer and agent components"""
        mock_answerer = MagicMock()
        mock_agent = MagicMock()

        job_applier.set_answerer_and_agent(mock_answerer, mock_agent)

        assert job_applier.llm_answerer_component == mock_answerer
        assert job_applier.llm_agent_component == mock_agent

    def test_set_resume(self, job_applier):
        """Test setting resume data"""
        resume_data = {
            "personal_information": {"name": "John Doe"},
            "experience": ["Software Engineer at Company A"],
        }

        job_applier.set_resume(resume_data)

        assert job_applier.resume == resume_data

    def test_set_resume_generator_manager(self, job_applier):
        """Test setting resume generator manager"""
        mock_generator = MagicMock()

        job_applier.set_resume_generator_manager(mock_generator)

        assert job_applier.resume_generator_manager == mock_generator


class TestSetParameters:
    """Test set_parameters method"""

    def test_set_parameters_basic_attributes(self, job_applier):
        """Test setting basic parameters"""
        # Mock the loading methods to avoid file I/O
        with (
            patch.object(job_applier, "_load_companies_from_yaml", return_value={}),
            patch.object(job_applier, "_load_data_from_yaml", return_value=[]),
            patch.object(job_applier, "_load_cache", return_value=JobManagerCache()),
        ):
            parameters = {
                "apply_once_at_company": True,
                "job_blacklist": ["BadCompany Inc", "Evil Corp"],
            }

            job_applier.set_parameters(parameters)

            assert job_applier.apply_once_at_company is True
            assert "badcompany inc" in job_applier.job_blacklist
            assert "evil corp" in job_applier.job_blacklist
            assert job_applier.applies_num == 0


class TestCacheManagement:
    """Test cache loading and writing"""

    def test_load_cache_empty(self, job_applier):
        """Test loading cache when file doesn't exist"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            cache = job_applier._load_cache()

            assert isinstance(cache, JobManagerCache)
            assert cache.last_run is None
            assert cache.last_apply is None
            assert cache.success_applies_num == 0
            assert cache.total_applies_num == 0

    def test_load_cache_with_data(self, job_applier):
        """Test loading cache with existing data"""
        cache_data = {
            "last_run": "2025-10-14T10:00:00",
            "last_apply": "2025-10-14T11:00:00",
            "success_applies_num": 5,
            "total_applies_num": 100,
        }

        with patch("builtins.open", mock_open()), patch("yaml.safe_load", return_value=cache_data):
            cache = job_applier._load_cache()

            assert cache.last_run == "2025-10-14T10:00:00"
            assert cache.last_apply == "2025-10-14T11:00:00"
            assert cache.success_applies_num == 5
            assert cache.total_applies_num == 100

    def test_write_the_last_search_time(self, job_applier):
        """Test writing cache to file"""
        job_applier.cache = JobManagerCache(
            last_run="2025-10-14T10:00:00",
            success_applies_num=10,
            total_applies_num=50,
        )

        mock_file = mock_open()
        with (
            patch("builtins.open", mock_file),
            patch("src.job_manager.job_manager.save_yaml_file") as mock_save,
        ):
            job_applier._write_the_last_search_time()

            mock_save.assert_called_once()
            call_args = mock_save.call_args[0]
            assert call_args[1]["last_run"] == "2025-10-14T10:00:00"
            assert call_args[1]["success_applies_num"] == 10
            assert call_args[1]["total_applies_num"] == 50


class TestTimeChecking:
    """Test time-related checking methods"""

    def test_check_the_last_search_time_no_previous_run(self, job_applier):
        """Test when there's no previous run"""
        job_applier.cache = JobManagerCache()

        result = job_applier.check_the_last_search_time()

        assert result is True

    def test_check_the_last_search_time_24_hours_passed(self, job_applier):
        """Test when 24 hours have passed since last run"""
        past_time = datetime.now() - timedelta(hours=25)
        job_applier.cache = JobManagerCache(last_run=past_time.isoformat())

        result = job_applier.check_the_last_search_time()

        assert result is True

    def test_check_the_last_search_time_too_soon(self, job_applier):
        """Test when less than 24 hours have passed"""
        recent_time = datetime.now() - timedelta(hours=12)
        job_applier.cache = JobManagerCache(last_run=recent_time.isoformat())
        job_applier.previous_apply_number = 0

        result = job_applier.check_the_last_search_time()

        assert result is False

    def test_check_previous_apply_number_no_previous(self, job_applier):
        """Test when there's no previous application"""
        job_applier.cache = JobManagerCache()

        result = job_applier._check_the_previous_apply_number()

        assert result == 0

    def test_check_previous_apply_number_recent_apply(self, job_applier):
        """Test when there's a recent application (< 59 minutes ago)"""
        recent_time = datetime.now() - timedelta(minutes=30)
        job_applier.cache = JobManagerCache(
            last_apply=recent_time.isoformat(), success_applies_num=5
        )

        result = job_applier._check_the_previous_apply_number()

        assert result == 5

    def test_check_previous_apply_number_old_apply(self, job_applier):
        """Test when last application was more than 59 minutes ago"""
        old_time = datetime.now() - timedelta(hours=2)
        job_applier.cache = JobManagerCache(last_apply=old_time.isoformat(), success_applies_num=5)

        result = job_applier._check_the_previous_apply_number()

        assert result == 0


class TestJobInfoCollection:
    """Test job info collection methods"""

    def test_collect_job_info(self, job_applier):
        """Test collecting job information"""
        job_applier._collect_job_info(
            company_job_title="Software Engineer",
            company_name="Tech Corp",
            job_link="https://linkedin.com/jobs/view/12345",
            reason="Missing information",
        )

        assert len(job_applier.jobs_no_info) == 1
        job_info = job_applier.jobs_no_info[0]
        assert job_info["job_title"] == "Software Engineer"
        assert job_info["company_name"] == "Tech Corp"
        assert job_info["url"] == "https://linkedin.com/jobs/view/12345"
        assert job_info["skip_reason"] == "Missing information"


class TestSkillStatistics:
    """Test skill statistics management"""

    def test_update_skill_stat_simple_skills(self, job_applier):
        """Test updating skill statistics with simple skills"""
        with patch.object(job_applier, "_save_data_to_yaml"):
            job_applier.skill_stat = {}

            skills = ["Python", "JavaScript", "Python"]
            job_applier._update_skill_stat(skills)

            assert job_applier.skill_stat["Python"] == 2
            assert job_applier.skill_stat["JavaScript"] == 1

    def test_update_skill_stat_with_semicolons(self, job_applier):
        """Test updating skill statistics with semicolon-separated skills"""
        with patch.object(job_applier, "_save_data_to_yaml"):
            job_applier.skill_stat = {}

            skills = ["Python; JavaScript", "Docker"]
            job_applier._update_skill_stat(skills)

            assert job_applier.skill_stat["Python"] == 1
            assert job_applier.skill_stat["JavaScript"] == 1
            assert job_applier.skill_stat["Docker"] == 1

    def test_process_skill_string(self, job_applier):
        """Test processing skill string with semicolons"""
        skill_string = "Python; JavaScript; Docker"

        result = job_applier._process_skill_string(skill_string)

        assert result == ["Python", "JavaScript", "Docker"]

    def test_process_skill_string_with_special_chars(self, job_applier):
        """Test processing skill string with special characters"""
        skill_string = "Python@3.9; Node.js!"

        result = job_applier._process_skill_string(skill_string)

        assert result == ["Python39", "Nodejs"]


class TestCompanyManagement:
    """Test company saving and loading"""

    def test_is_blacklisted(self, job_applier):
        """Test checking if company is blacklisted"""
        job_applier.job_blacklist = ["bad company", "evil corp"]

        assert job_applier._is_blacklisted("bad company") is True
        assert job_applier._is_blacklisted("good company") is False

    def test_save_company_success(self, job_applier):
        """Test saving company to success list"""
        with patch.object(job_applier, "_save_company_to_yaml"):
            job_applier.success_companies = {}
            job_applier.skipped_companies = {}
            job_applier.failed_companies = {}

            job = Job(
                job_title="Software Engineer",
                company_name="Tech Corp",
                url="https://linkedin.com/jobs/view/12345",
            )
            vacancy = {"url": "https://linkedin.com/jobs/view/12345"}
            apply_result = ("Success", "")

            job_applier._save_company(job, apply_result, vacancy)

            assert "Tech Corp" in job_applier.success_companies
            assert len(job_applier.success_companies["Tech Corp"]) == 1
            assert job_applier.success_companies["Tech Corp"][0]["job_title"] == "Software Engineer"

    def test_save_company_skip(self, job_applier):
        """Test saving company to skipped list"""
        with patch.object(job_applier, "_save_company_to_yaml"):
            job_applier.success_companies = {}
            job_applier.skipped_companies = {}
            job_applier.failed_companies = {}

            job = Job(
                job_title="Software Engineer",
                company_name="Tech Corp",
                url="https://linkedin.com/jobs/view/12345",
            )
            vacancy = {"url": "https://linkedin.com/jobs/view/12345"}
            apply_result = ("Skip", "Not interesting")

            job_applier._save_company(job, apply_result, vacancy)

            assert "Tech Corp" in job_applier.skipped_companies

    def test_save_company_failed(self, job_applier):
        """Test saving company to failed list"""
        with patch.object(job_applier, "_save_company_to_yaml"):
            job_applier.success_companies = {}
            job_applier.skipped_companies = {}
            job_applier.failed_companies = {}

            job = Job(
                job_title="Software Engineer",
                company_name="Tech Corp",
                url="https://linkedin.com/jobs/view/12345",
            )
            vacancy = {"url": "https://linkedin.com/jobs/view/12345"}
            apply_result = ("Error", "Form submission failed")

            job_applier._save_company(job, apply_result, vacancy)

            assert "Tech Corp" in job_applier.failed_companies

    def test_load_companies_from_yaml_not_found(self, job_applier):
        """Test loading companies when file doesn't exist"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = job_applier._load_companies_from_yaml("nonexistent.yaml")

            assert result == {}

    def test_load_companies_from_yaml_success(self, job_applier):
        """Test loading companies from existing file"""
        companies_data = {
            "Tech Corp": [{"job_title": "Engineer", "url": "http://test.com"}],
            "Another Corp": [{"job_title": "Developer", "url": "http://test2.com"}],
        }

        with (
            patch("builtins.open", mock_open()),
            patch("yaml.safe_load", return_value=companies_data),
        ):
            result = job_applier._load_companies_from_yaml("success.yaml")

            assert result == companies_data
            assert "Tech Corp" in result
            assert "Another Corp" in result


class TestJobSeenChecking:
    """Test job duplicate detection"""

    def test_job_is_already_seen_not_seen(self, job_applier):
        """Test when job has not been seen before"""
        job_applier.success_companies = {}
        job_applier.apply_once_at_company = True

        job = Job(job_title="Software Engineer", company_name="New Company")

        is_seen, reason = job_applier._job_is_already_seen(job)

        assert is_seen is False
        assert reason == ""

    def test_job_is_already_seen_same_company_apply_once(self, job_applier):
        """Test when company was seen and apply_once_at_company is True"""
        job_applier.success_companies = {
            "Tech Corp": [{"job_title": "Other Position", "url": "http://test.com"}]
        }
        job_applier.apply_once_at_company = True

        job = Job(job_title="Software Engineer", company_name="Tech Corp")

        with patch("src.job_manager.job_manager.COLLECT_INFO_MODE", False):
            is_seen, reason = job_applier._job_is_already_seen(job)

        assert is_seen is True
        assert "company has already been encountered" in reason

    def test_job_is_already_seen_same_job_title(self, job_applier):
        """Test when same job title at same company was seen"""
        job_applier.success_companies = {
            "Tech Corp": [{"job_title": "Software Engineer", "url": "http://test.com"}]
        }
        job_applier.apply_once_at_company = False
        job = Job(job_title="Software Engineer", company_name="Tech Corp")
        with patch("src.job_manager.job_manager.COLLECT_INFO_MODE", False):
            is_seen, reason = job_applier._job_is_already_seen(job)

        assert is_seen is True
        assert "vacancy has already been encountered" in reason


class TestInterestingJobs:
    """Test interesting job saving"""

    def test_save_interesting_job(self, job_applier):
        """Test saving an interesting job"""
        with patch.object(job_applier, "_save_data_to_yaml"):
            job_applier.interesting_jobs = []
            job_applier.job_key_skills = ["Python", "Docker"]

            job = Job(
                job_title="Senior Engineer",
                company_name="Tech Corp",
                url="https://linkedin.com/jobs/view/12345",
            )

            job_applier._save_interesting_job(job, score=85, reasoning="Great fit")

            assert len(job_applier.interesting_jobs) == 1
            saved_job = job_applier.interesting_jobs[0]
            assert saved_job.job_title == "Senior Engineer"
            assert saved_job.company_name == "Tech Corp"
            assert saved_job.interest_score == 85
            assert saved_job.interest_reason == "Great fit"
            assert saved_job.skills == ["Python", "Docker"]

    def test_save_interesting_job_sorted(self, job_applier):
        """Test that interesting jobs are sorted by score"""
        with patch.object(job_applier, "_save_data_to_yaml"):
            job_applier.interesting_jobs = []
            job_applier.job_key_skills = []

            job1 = Job(
                job_title="Job 1", company_name="Corp 1", url="https://linkedin.com/jobs/view/1"
            )
            job2 = Job(
                job_title="Job 2", company_name="Corp 2", url="https://linkedin.com/jobs/view/2"
            )
            job3 = Job(
                job_title="Job 3", company_name="Corp 3", url="https://linkedin.com/jobs/view/3"
            )

            job_applier._save_interesting_job(job1, score=70, reasoning="Good")
            job_applier._save_interesting_job(job2, score=90, reasoning="Excellent")
            job_applier._save_interesting_job(job3, score=80, reasoning="Very good")

            assert job_applier.interesting_jobs[0].interest_score == 90
            assert job_applier.interesting_jobs[1].interest_score == 80
            assert job_applier.interesting_jobs[2].interest_score == 70


class TestDataPersistence:
    """Test data saving and loading"""

    def test_save_data_to_yaml(self, job_applier):
        """Test saving data to YAML file without real I/O"""
        data = {"key1": "value1", "key2": "value2"}
        mock_path = Path("/mock/output/test_data.yaml")

        with (
            patch.object(job_applier, "_define_output_file", return_value=mock_path),
            patch("builtins.open", mock_open()),
            patch("src.job_manager.job_manager.save_yaml_file") as mock_save,
        ):
            job_applier._save_data_to_yaml(data, "test_data.yaml")

            mock_save.assert_called_once()
            args, kwargs = mock_save.call_args
            assert args[0] == mock_path
            assert args[1] == data

    def test_load_data_from_yaml_success(self, job_applier):
        """Test loading data from YAML file without real I/O"""
        data = {"key1": "value1", "key2": "value2"}
        mock_path = Path("/mock/output/test_data.yaml")

        with (
            patch.object(job_applier, "_define_output_file", return_value=mock_path),
            patch("builtins.open", mock_open()),
            patch("yaml.safe_load", return_value=data),
        ):
            loaded_data = job_applier._load_data_from_yaml("test_data.yaml")

            assert loaded_data == data

    def test_load_data_from_yaml_not_found(self, job_applier):
        """Test loading data when file doesn't exist (no I/O)"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            loaded_data = job_applier._load_data_from_yaml("nonexistent.yaml")

            assert loaded_data == {}

    def test_load_data_from_yaml_answers_returns_list(self, job_applier):
        """Test that loading answers.yaml returns list when file not found (no I/O)"""
        mock_path = Path("/mock/output/nonexistent_answers.yaml")

        with (
            patch.object(job_applier, "_define_output_file", return_value=mock_path),
            patch("builtins.open", side_effect=FileNotFoundError),
        ):
            loaded_data = job_applier._load_data_from_yaml("answers.yaml")

            assert loaded_data == []


class TestDefineOutputFile:
    """Test output file path definition"""

    def test_define_output_file(self):
        """Test defining output file path"""
        result = JobApplier._define_output_file("test.yaml")

        # Just verify it returns a path containing the filename
        assert "test.yaml" in str(result)
        assert "data/output" in str(result) or "data\\output" in str(result)


class TestGetApplyResult:
    """Test get_apply_result method"""

    def test_get_apply_result_success(self, job_applier):
        """Test get_apply_result with successful application"""
        with (
            patch.object(job_applier, "_save_company"),
            patch("src.job_manager.job_manager.save_yaml_file"),
        ):
            job_applier.cache = JobManagerCache()
            job_applier.applies_num = 0
            job_applier.success_applies_num = 0
            job_applier.total_applies_num = 0
            job_applier.max_applies_num = 50
            job_applier.success_companies = {}
            job_applier.skipped_companies = {}
            job_applier.failed_companies = {}

            job = Job(
                job_title="Engineer",
                company_name="Tech Corp",
                url="https://linkedin.com/jobs/view/12345",
            )
            vacancy = {"url": "https://linkedin.com/jobs/view/12345"}
            apply_result = ("Success", "")
            minimum_job_time = 0  # No waiting needed

            result = job_applier.get_apply_result(apply_result, job, vacancy, minimum_job_time)

            assert job_applier.applies_num == 1
            assert job_applier.success_applies_num == 1
            assert job_applier.total_applies_num == 1
            assert result == "Success"

    def test_get_apply_result_skip(self, job_applier):
        """Test get_apply_result with skipped application"""
        with (patch.object(job_applier, "_save_company"),):
            job_applier.cache = JobManagerCache()
            job_applier.applies_num = 0
            job_applier.success_applies_num = 0
            job_applier.total_applies_num = 0
            job_applier.max_applies_num = 50
            job_applier.success_companies = {}
            job_applier.skipped_companies = {}
            job_applier.failed_companies = {}

            job = Job(
                job_title="Engineer",
                company_name="Tech Corp",
                url="https://linkedin.com/jobs/view/12345",
            )
            vacancy = {"url": "https://linkedin.com/jobs/view/12345"}
            apply_result = ("Skip", "Not interesting")
            minimum_job_time = 0

            result = job_applier.get_apply_result(apply_result, job, vacancy, minimum_job_time)

            assert job_applier.applies_num == 1
            assert job_applier.success_applies_num == 0  # No success
            assert result == "Skip"

    def test_get_apply_result_limit_reached(self, job_applier):
        """Test get_apply_result when limit is reached"""
        with (
            patch.object(job_applier, "_save_company"),
            patch("src.job_manager.job_manager.save_yaml_file"),
        ):
            job_applier.cache = JobManagerCache()
            job_applier.applies_num = 0
            job_applier.success_applies_num = 49
            job_applier.total_applies_num = 0
            job_applier.max_applies_num = 50
            job_applier.success_companies = {}
            job_applier.skipped_companies = {}
            job_applier.failed_companies = {}

            job = Job(
                job_title="Engineer",
                company_name="Tech Corp",
                url="https://linkedin.com/jobs/view/12345",
            )
            vacancy = {"url": "https://linkedin.com/jobs/view/12345"}
            apply_result = ("Success", "")
            minimum_job_time = 0

            result = job_applier.get_apply_result(apply_result, job, vacancy, minimum_job_time)

            assert job_applier.success_applies_num == 50
            assert result == "Limit"

    def test_get_apply_result_limit_status(self, job_applier):
        """Test get_apply_result when apply_result is Limit"""
        with (patch.object(job_applier, "_save_company"),):
            job_applier.cache = JobManagerCache()
            job_applier.applies_num = 0
            job_applier.success_applies_num = 10
            job_applier.total_applies_num = 0
            job_applier.max_applies_num = 50
            job_applier.success_companies = {}
            job_applier.skipped_companies = {}
            job_applier.failed_companies = {}

            job = Job(
                job_title="Engineer",
                company_name="Tech Corp",
                url="https://linkedin.com/jobs/view/12345",
            )
            vacancy = {"url": "https://linkedin.com/jobs/view/12345"}
            apply_result = ("Limit", "")
            minimum_job_time = 0

            result = job_applier.get_apply_result(apply_result, job, vacancy, minimum_job_time)

            # When result is "Limit", company should not be saved
            assert result == "Limit"


class TestExtractSkillsFromVacancy:
    """Test skills extraction from vacancy"""

    def test_extract_skills_from_vacancy(self, job_applier):
        """Test extracting skills from vacancy using LLM"""
        mock_llm_answerer = MagicMock()
        mock_llm_answerer.extract_skills_from_vacancy.return_value = [
            "Python",
            "Docker",
            "Kubernetes",
        ]
        job_applier.llm_answerer_component = mock_llm_answerer

        job = Job(
            job_description="We are looking for a developer with Python, Docker, and Kubernetes experience"
        )

        job_applier._extract_skills_from_vacancy(job)

        assert job_applier.job_key_skills == ["Python", "Docker", "Kubernetes"]
        mock_llm_answerer.extract_skills_from_vacancy.assert_called_once_with(job.job_description)
