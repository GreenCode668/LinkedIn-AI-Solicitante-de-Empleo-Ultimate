"""
Unit tests for src/utils/json_to_readable.py

Tests cover all formatting and transformation functions for LinkedIn job and search configuration data.
"""

from src.utils.json_to_readable import (
    _format_value,
    _get_multiple_selected_options,
    _get_selected_option,
    _indent_text,
    transform_search_config_data,
    transform_vacancy_data,
)


class TestFormatValue:
    """Tests for _format_value function"""

    def test_format_none(self):
        """Test that None returns None"""
        assert _format_value(None) is None

    def test_format_boolean_true(self):
        """Test that True returns 'Да'"""
        assert _format_value(True) == "Да"

    def test_format_boolean_false(self):
        """Test that False returns 'Нет'"""
        assert _format_value(False) == "Нет"

    def test_format_string_normal(self):
        """Test normal string formatting"""
        assert _format_value("test string") == "test string"

    def test_format_string_with_whitespace(self):
        """Test string with leading/trailing whitespace gets stripped"""
        assert _format_value("  test  ") == "test"

    def test_format_empty_string(self):
        """Test empty string returns None"""
        assert _format_value("") is None

    def test_format_whitespace_only_string(self):
        """Test whitespace-only string returns None"""
        assert _format_value("   ") is None

    def test_format_list_normal(self):
        """Test list formatting with valid items"""
        assert _format_value(["item1", "item2", "item3"]) == "item1, item2, item3"

    def test_format_list_with_none(self):
        """Test list with None values filters them out"""
        assert _format_value(["item1", None, "item2"]) == "item1, item2"

    def test_format_list_with_empty_strings(self):
        """Test list with empty strings filters them out"""
        assert _format_value(["item1", "", "item2"]) == "item1, item2"

    def test_format_list_with_whitespace_strings(self):
        """Test list with whitespace-only strings filters them out"""
        assert _format_value(["item1", "   ", "item2"]) == "item1, item2"

    def test_format_empty_list(self):
        """Test empty list returns None"""
        assert _format_value([]) is None

    def test_format_list_only_empty_items(self):
        """Test list with only empty items returns None"""
        assert _format_value([None, "", "  "]) is None

    def test_format_list_with_numbers(self):
        """Test list with numbers"""
        assert _format_value([1, 2, 3]) == "1, 2, 3"

    def test_format_dict_normal(self):
        """Test dict with values returns the dict"""
        data = {"key": "value"}
        assert _format_value(data) == data

    def test_format_empty_dict(self):
        """Test empty dict returns None"""
        assert _format_value({}) is None

    def test_format_number_int(self):
        """Test integer formatting"""
        assert _format_value(42) == "42"

    def test_format_number_float(self):
        """Test float formatting"""
        assert _format_value(3.14) == "3.14"

    def test_format_number_zero(self):
        """Test zero formatting"""
        assert _format_value(0) == "0"


class TestIndentText:
    """Tests for _indent_text function"""

    def test_indent_normal_text(self):
        """Test indenting normal text"""
        result = _indent_text("line1\nline2\nline3")
        assert result == "  line1\n  line2\n  line3"

    def test_indent_single_line(self):
        """Test indenting single line"""
        result = _indent_text("single line")
        assert result == "  single line"

    def test_indent_custom_prefix(self):
        """Test custom prefix"""
        result = _indent_text("test", prefix="    ")
        assert result == "    test"

    def test_indent_none(self):
        """Test None returns empty string"""
        assert _indent_text(None) == ""

    def test_indent_empty_string(self):
        """Test empty string returns empty string"""
        assert _indent_text("") == ""

    def test_indent_whitespace_only(self):
        """Test whitespace-only string returns empty string"""
        assert _indent_text("   ") == ""


class TestGetSelectedOption:
    """Tests for _get_selected_option function"""

    def test_get_selected_option_found(self):
        """Test getting a selected option"""
        group_data = {"option1": False, "option2": True, "option3": False}
        option_map = {"option1": "Option 1", "option2": "Option 2", "option3": "Option 3"}
        assert _get_selected_option(group_data, option_map) == "Option 2"

    def test_get_selected_option_not_found(self):
        """Test when no option is selected"""
        group_data = {"option1": False, "option2": False}
        option_map = {"option1": "Option 1", "option2": "Option 2"}
        assert _get_selected_option(group_data, option_map) is None

    def test_get_selected_option_not_in_map(self):
        """Test when selected option is not in map"""
        group_data = {"unknown": True}
        option_map = {"option1": "Option 1"}
        assert _get_selected_option(group_data, option_map) == "unknown"

    def test_get_selected_option_invalid_input(self):
        """Test with invalid input"""
        assert _get_selected_option(None, {}) is None
        assert _get_selected_option("not a dict", {}) is None


class TestGetMultipleSelectedOptions:
    """Tests for _get_multiple_selected_options function"""

    def test_get_multiple_selected_options(self):
        """Test getting multiple selected options"""
        group_data = {"option1": True, "option2": False, "option3": True}
        option_map = {"option1": "Option 1", "option2": "Option 2", "option3": "Option 3"}
        result = _get_multiple_selected_options(group_data, option_map)
        assert result == "Option 1, Option 3"

    def test_get_multiple_selected_options_none_selected(self):
        """Test when no options are selected"""
        group_data = {"option1": False, "option2": False}
        option_map = {"option1": "Option 1", "option2": "Option 2"}
        assert _get_multiple_selected_options(group_data, option_map) is None

    def test_get_multiple_selected_options_single(self):
        """Test with single selected option"""
        group_data = {"option1": True, "option2": False}
        option_map = {"option1": "Option 1", "option2": "Option 2"}
        assert _get_multiple_selected_options(group_data, option_map) == "Option 1"

    def test_get_multiple_selected_options_invalid_input(self):
        """Test with invalid input"""
        assert _get_multiple_selected_options(None, {}) is None
        assert _get_multiple_selected_options("not a dict", {}) is None


class TestTransformVacancyData:
    """Tests for transform_vacancy_data function"""

    def test_transform_complete_vacancy_data(self):
        """Test transformation of complete vacancy data"""
        data = {
            "job_title": "Senior Python Developer",
            "company_name": "TechCorp Inc",
            # "url": "https://www.linkedin.com/jobs/view/123456789",
            "job_description": "We are looking for a Senior Python Developer.",
            "company_description": "TechCorp Inc is a leading technology company.",
            "skills": ["Python", "Django", "FastAPI"],
            "preferences": ["Full-time", "Remote"],
        }
        result = transform_vacancy_data(data)

        assert "LinkedIn vacancy information" in result
        assert "Vacancy name: Senior Python Developer" in result
        assert "Company name: TechCorp Inc" in result
        # assert "Vacancy URL: https://www.linkedin.com/jobs/view/123456789" in result
        assert "VACANCY DESCRIPTION:" in result
        assert "We are looking for a Senior Python Developer." in result
        assert "COMPANY INFORMATION:" in result
        assert "TechCorp Inc is a leading technology company." in result
        assert "REQUIRED SKILLS:" in result
        assert "Python, Django, FastAPI" in result
        assert "WORK PREFERENCES:" in result
        assert "Full-time, Remote" in result

    def test_transform_minimal_vacancy_data(self):
        """Test transformation of minimal vacancy data"""
        data = {"job_title": "Developer", "company_name": "Startup Inc"}
        result = transform_vacancy_data(data)

        assert "LinkedIn vacancy information" in result
        assert "Vacancy name: Developer" in result
        assert "Company name: Startup Inc" in result
        assert "VACANCY DESCRIPTION:" not in result
        assert "COMPANY INFORMATION:" not in result

    def test_transform_vacancy_data_with_empty_fields(self):
        """Test transformation ignores empty fields"""
        data = {
            "job_title": "Developer",
            "company_name": "Company",
            "job_description": "",
            "company_description": None,
            "skills": [],
            "preferences": "",
        }
        result = transform_vacancy_data(data)

        assert "VACANCY DESCRIPTION:" not in result
        assert "COMPANY INFORMATION:" not in result
        assert "REQUIRED SKILLS:" not in result
        assert "WORK PREFERENCES:" not in result

    def test_transform_empty_vacancy_data(self):
        """Test transformation of empty data"""
        assert "No data to display in vacancy" in transform_vacancy_data({})

    def test_transform_none_vacancy_data(self):
        """Test transformation of None"""
        assert "No data to display in vacancy" in transform_vacancy_data(None)

    def test_transform_invalid_vacancy_data(self):
        """Test transformation of invalid data type"""
        assert "No data to display in vacancy" in transform_vacancy_data("not a dict")


class TestTransformSearchConfigData:
    """Tests for transform_search_config_data function"""

    def test_transform_complete_search_config(self):
        """Test transformation of complete search configuration"""
        data = {
            "positions": ["Software Engineer", "Python Developer"],
            "locations": ["Germany", "Remote"],
            "remote": True,
            "hybrid": True,
            "onsite": False,
            "experience_level": {
                "entry": True,
                "associate": False,
                "mid_senior_level": True,
                "director": False,
                "executive": False,
                "internship": False,
            },
            "job_types": {
                "full_time": True,
                "contract": False,
                "part_time": True,
                "temporary": False,
                "volunteer": False,
                "internship": False,
                "other": False,
            },
            "date": {"all_time": False, "month": False, "week": True, "day_24_hours": False},
            "apply_once_at_company": True,
            "company_blacklist": ["wayfair", "Crossover"],
            "title_blacklist": ["word1", "word2"],
            "location_blacklist": ["Brazil"],
        }
        result = transform_search_config_data(data)

        assert "LinkedIn Search Parameters" in result
        assert "MAIN SEARCH PARAMETERS:" in result
        assert "Positions: Software Engineer, Python Developer" in result
        assert "Locations: Germany, Remote" in result
        assert "WORK ARRANGEMENT:" in result
        assert "Remote work" in result
        assert "Hybrid work" in result
        assert "On-site work" not in result
        assert "EXPERIENCE LEVEL:" in result
        assert "Entry level" in result
        assert "Mid-senior level" in result
        assert "JOB TYPES:" in result
        assert "Full-time" in result
        assert "Part-time" in result
        assert "DATE POSTED:" in result
        assert "Past week" in result
        assert "APPLICATION SETTINGS:" in result
        assert "Apply only once per company: Да" in result
        assert "BLACKLISTS:" in result
        assert "Company blacklist: wayfair, Crossover" in result
        assert "Title blacklist: word1, word2" in result
        assert "Location blacklist: Brazil" in result

    def test_transform_minimal_search_config(self):
        """Test transformation of minimal search configuration"""
        data = {"positions": ["Developer"], "remote": True}
        result = transform_search_config_data(data)

        assert "LinkedIn Search Parameters" in result
        assert "Positions: Developer" in result
        assert "WORK ARRANGEMENT:" in result
        assert "Remote work" in result

    def test_transform_search_config_no_work_arrangement(self):
        """Test when no work arrangement is selected"""
        data = {"positions": ["Developer"], "remote": False, "hybrid": False, "onsite": False}
        result = transform_search_config_data(data)

        assert "WORK ARRANGEMENT:" not in result

    def test_transform_search_config_all_work_arrangements(self):
        """Test when all work arrangements are selected"""
        data = {"remote": True, "hybrid": True, "onsite": True}
        result = transform_search_config_data(data)

        assert "Remote work" in result
        assert "Hybrid work" in result
        assert "On-site work" in result

    def test_transform_search_config_experience_levels(self):
        """Test all experience levels"""
        data = {
            "experience_level": {
                "internship": True,
                "entry": True,
                "associate": True,
                "mid_senior_level": True,
                "director": True,
                "executive": True,
            }
        }
        result = transform_search_config_data(data)

        assert "Internship" in result
        assert "Entry level" in result
        assert "Associate level" in result
        assert "Mid-senior level" in result
        assert "Director level" in result
        assert "Executive level" in result

    def test_transform_search_config_job_types(self):
        """Test all job types"""
        data = {
            "job_types": {
                "full_time": True,
                "contract": True,
                "part_time": True,
                "temporary": True,
                "volunteer": True,
                "internship": True,
                "other": True,
            }
        }
        result = transform_search_config_data(data)

        assert "Full-time" in result
        assert "Contract" in result
        assert "Part-time" in result
        assert "Temporary" in result
        assert "Volunteer" in result
        assert "Internship" in result
        assert "Other" in result

    def test_transform_search_config_date_posted(self):
        """Test all date posted options"""
        data = {"date": {"all_time": True, "month": False, "week": False, "day_24_hours": False}}
        result = transform_search_config_data(data)

        assert "All time" in result

    def test_transform_search_config_apply_once_false(self):
        """Test apply once at company set to False"""
        data = {"apply_once_at_company": False}
        result = transform_search_config_data(data)

        assert "Apply only once per company: Нет" in result

    def test_transform_search_config_empty_blacklists(self):
        """Test with empty blacklists"""
        data = {"company_blacklist": [], "title_blacklist": [], "location_blacklist": []}
        result = transform_search_config_data(data)

        assert "BLACKLISTS:" not in result

    def test_transform_empty_search_config(self):
        """Test transformation of empty data"""
        assert "No data available for" in transform_search_config_data({})

    def test_transform_none_search_config(self):
        """Test transformation of None"""
        assert "No data available for" in transform_search_config_data(None)

    def test_transform_invalid_search_config(self):
        """Test transformation of invalid data type"""
        assert "No data available for" in transform_search_config_data("not a dict")


class TestIntegration:
    """Integration tests for complete workflows"""

    def test_full_vacancy_workflow(self):
        """Test complete vacancy data transformation workflow"""
        data = {
            "job_title": "Machine Learning Engineer",
            "company_name": "AI Solutions Ltd",
            "url": "https://www.linkedin.com/jobs/view/987654321",
            "job_description": "Build cutting-edge ML models.\nWork with TensorFlow and PyTorch.",
            "company_description": "We specialize in AI solutions.\nFounded in 2020.",
            "skills": ["Python", "TensorFlow", "PyTorch", "Kubernetes"],
            "preferences": ["Remote", "Full-time", "Competitive salary"],
        }
        result = transform_vacancy_data(data)

        # Verify structure
        assert result.startswith("LinkedIn vacancy information")
        assert "===" in result

        # Verify all sections present
        sections = [
            "Machine Learning Engineer",
            "AI Solutions Ltd",
            "VACANCY DESCRIPTION:",
            "COMPANY INFORMATION:",
            "REQUIRED SKILLS:",
            "WORK PREFERENCES:",
        ]
        for section in sections:
            assert section in result

    def test_full_search_config_workflow(self):
        """Test complete search config transformation workflow"""
        data = {
            "positions": ["Data Scientist", "ML Engineer", "AI Researcher"],
            "locations": ["London", "Paris", "Remote"],
            "remote": True,
            "hybrid": False,
            "onsite": False,
            "experience_level": {"mid_senior_level": True, "director": True},
            "job_types": {"full_time": True, "contract": True},
            "date": {"week": True},
            "apply_once_at_company": True,
            "company_blacklist": ["Company A", "Company B"],
            "title_blacklist": ["Junior", "Intern"],
            "location_blacklist": ["City X"],
        }
        result = transform_search_config_data(data)

        # Verify structure
        assert result.startswith("LinkedIn Search Parameters")
        assert "===" in result

        # Verify all sections present
        sections = [
            "MAIN SEARCH PARAMETERS:",
            "WORK ARRANGEMENT:",
            "EXPERIENCE LEVEL:",
            "JOB TYPES:",
            "DATE POSTED:",
            "APPLICATION SETTINGS:",
            "BLACKLISTS:",
        ]
        for section in sections:
            assert section in result

    def test_edge_case_mixed_empty_and_valid_data(self):
        """Test with mixture of empty and valid data"""
        data = {
            "job_title": "Developer",
            "company_name": "",  # Empty
            "url": None,  # None
            "job_description": "Valid description",
            "company_description": "   ",  # Whitespace
            "skills": ["Python", "", None, "JavaScript"],  # Mixed
            "preferences": [],  # Empty list
        }
        result = transform_vacancy_data(data)

        assert "Vacancy name: Developer" in result
        assert "Company name:" not in result or "Company name: \n" not in result
        assert "VACANCY DESCRIPTION:" in result
        assert "Valid description" in result
        assert "COMPANY INFORMATION:" not in result
        assert "Python, JavaScript" in result
        assert "WORK PREFERENCES:" not in result
