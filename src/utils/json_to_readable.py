from typing import Any, Dict


def _format_value(value: Any) -> Any:
    """
    Formats a value for display.
    Returns None if the value is considered empty (None, empty string, empty list/dict).
    Converts booleans to 'Да'/'Нет'.
    Joins list items into a comma-separated string, returning None if list is empty or contains only empty items.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if isinstance(value, str):
        return value.strip() if value.strip() else None
    if isinstance(value, list):
        # Filter out empty strings or None from list before joining
        filtered_list = [
            str(item) for item in value if item is not None and str(item).strip() != ""
        ]
        return ", ".join(filtered_list) if filtered_list else None
    if isinstance(value, dict):
        return value if value else None  # Return dict if not empty, else None (for specific checks)
    return str(value)  # For numbers, etc.


def _indent_text(text: str, prefix: str = "  ") -> str:
    """Indents a block of text. Returns empty string if text is None or empty/whitespace."""
    formatted_text = _format_value(text)
    if not formatted_text:
        return ""
    return "\n".join(prefix + line for line in formatted_text.splitlines())


def transform_vacancy_data(data: Dict[str, Any]) -> str:
    """
    Transforms LinkedIn job data into a human-readable string.
    Fields/sections are omitted if their data is missing or empty.
    """
    if not isinstance(data, dict) or not data:
        return "No data to display in vacancy."

    title = "LinkedIn vacancy information"
    content_lines = []

    # Main job information
    main_info_lines = []
    for key, label in [
        ("job_title", "Vacancy name"),
        ("company_name", "Company name"),
        # ("url", "Vacancy URL"),
    ]:
        val = _format_value(data.get(key))
        if val:
            main_info_lines.append(f"{label}: {val}")  # No indent for top-level info

    if main_info_lines:
        content_lines.extend(main_info_lines)

    # Job Description
    about_job = _indent_text(data.get("job_description"), "  ")
    if about_job:
        content_lines.append("\nVACANCY DESCRIPTION:")
        content_lines.append(about_job)

    # Company Information
    about_company = _indent_text(data.get("company_description"), "  ")
    if about_company:
        content_lines.append("\nCOMPANY INFORMATION:")
        content_lines.append(about_company)

    # Skills and Requirements
    skills = _format_value(data.get("skills"))
    if skills:
        content_lines.append("\nREQUIRED SKILLS:")
        content_lines.append(f"  {skills}")

    # Work Preferences
    preferences = _format_value(data.get("preferences"))
    if preferences:
        content_lines.append("\nWORK PREFERENCES:")
        content_lines.append(f"  {preferences}")

    if not content_lines:
        return f"No data to display in {title.lower()}."

    final_output = [title, "=" * 3]
    final_output.extend(content_lines)
    return "\n".join(final_output)


# Helpers for search_config
def _get_selected_option(group_data: Dict[str, Any], option_map: Dict[str, Any]) -> Any:
    """Get a selected option from a dictionary"""
    if not isinstance(group_data, dict):
        return None
    for key, value in group_data.items():
        if value is True:
            return option_map.get(key, key)
    return None


def _get_multiple_selected_options(group_data: Dict[str, Any], option_map: Dict[str, Any]) -> Any:
    """Get multiple selected options from a dictionary"""
    if not isinstance(group_data, dict):
        return None
    selected = [option_map.get(k, k) for k, v in group_data.items() if v is True]
    return ", ".join(selected) if selected else None


def transform_search_config_data(data: Dict[str, Any]) -> str:
    """
    Transforms LinkedIn search configuration YAML data into a human-readable string.
    Fields/sections are omitted if their data is missing or empty.
    """
    if not isinstance(data, dict) or not data:
        return "No data available for search configuration display."

    title = "LinkedIn Search Parameters"
    content_lines = []

    # --- Main search parameters ---
    sc_main_lines = []

    # Positions (job titles to search for)
    positions = _format_value(data.get("positions", []))
    if positions:
        sc_main_lines.append(f"  Positions: {positions}")

    # Locations
    locations = _format_value(data.get("locations", []))
    if locations:
        sc_main_lines.append(f"  Locations: {locations}")

    if sc_main_lines:
        content_lines.append("\nMAIN SEARCH PARAMETERS:")
        content_lines.extend(sc_main_lines)

    # --- Work arrangement ---
    work_arrangement_lines = []
    work_formats = []
    if data.get("remote"):
        work_formats.append("Remote work")
    if data.get("hybrid"):
        work_formats.append("Hybrid work")
    if data.get("onsite"):
        work_formats.append("On-site work")

    if work_formats:
        work_arrangement_lines.append(f"  Work format: {', '.join(work_formats)}")

    if work_arrangement_lines:
        content_lines.append("\nWORK ARRANGEMENT:")
        content_lines.extend(work_arrangement_lines)

    # --- Experience level ---
    experience_level = data.get("experience_level", {})
    if isinstance(experience_level, dict) and experience_level:
        exp_lines = []
        exp_map = {
            "internship": "Internship",
            "entry": "Entry level",
            "associate": "Associate level",
            "mid_senior_level": "Mid-senior level",
            "director": "Director level",
            "executive": "Executive level",
        }
        selected_levels = _get_multiple_selected_options(experience_level, exp_map)
        if selected_levels:
            exp_lines.append(f"  Experience level: {selected_levels}")

        if exp_lines:
            content_lines.append("\nEXPERIENCE LEVEL:")
            content_lines.extend(exp_lines)

    # --- Job types ---
    job_types = data.get("job_types", {})
    if isinstance(job_types, dict) and job_types:
        job_type_lines = []
        job_type_map = {
            "full_time": "Full-time",
            "contract": "Contract",
            "part_time": "Part-time",
            "temporary": "Temporary",
            "volunteer": "Volunteer",
            "internship": "Internship",
            "other": "Other",
        }
        selected_job_types = _get_multiple_selected_options(job_types, job_type_map)
        if selected_job_types:
            job_type_lines.append(f"  Job types: {selected_job_types}")

        if job_type_lines:
            content_lines.append("\nJOB TYPES:")
            content_lines.extend(job_type_lines)

    # --- Date posted ---
    date_posted = data.get("date", {})
    if isinstance(date_posted, dict) and date_posted:
        date_lines = []
        date_map = {
            "all_time": "All time",
            "month": "Past month",
            "week": "Past week",
            "day_24_hours": "Past 24 hours",
        }
        selected_dates = _get_multiple_selected_options(date_posted, date_map)
        if selected_dates:
            date_lines.append(f"  Date posted: {selected_dates}")

        if date_lines:
            content_lines.append("\nDATE POSTED:")
            content_lines.extend(date_lines)

    # --- Application settings ---
    apply_settings_lines = []
    apply_once = data.get("apply_once_at_company")
    if apply_once is not None:
        apply_settings_lines.append(f"  Apply only once per company: {_format_value(apply_once)}")

    if apply_settings_lines:
        content_lines.append("\nAPPLICATION SETTINGS:")
        content_lines.extend(apply_settings_lines)

    # --- Blacklists ---
    blacklist_lines = []

    company_blacklist = _format_value(data.get("company_blacklist", []))
    if company_blacklist:
        blacklist_lines.append(f"  Company blacklist: {company_blacklist}")

    title_blacklist = _format_value(data.get("title_blacklist", []))
    if title_blacklist:
        blacklist_lines.append(f"  Title blacklist: {title_blacklist}")

    location_blacklist = _format_value(data.get("location_blacklist", []))
    if location_blacklist:
        blacklist_lines.append(f"  Location blacklist: {location_blacklist}")

    if blacklist_lines:
        content_lines.append("\nBLACKLISTS:")
        content_lines.extend(blacklist_lines)

    if not content_lines:
        return f"No data available for {title.lower()} display."

    final_output = [title, "=" * 3]
    final_output.extend(content_lines)
    return "\n".join(final_output)


if __name__ == "__main__":
    # Test data for LinkedIn job vacancy
    linkedin_job_data = {
        "job_title": "Senior Python Developer",
        "company_name": "TechCorp Inc",
        "url": "https://www.linkedin.com/jobs/view/123456789",
        "id": "123456789",
        "about_the_job": "We are looking for a Senior Python Developer to join our team. You will be responsible for developing and maintaining our backend services using Python, Django, and FastAPI.",
        "about_the_company": "TechCorp Inc is a leading technology company specializing in innovative solutions for enterprise clients. Founded in 2010, we have grown to serve over 1000 clients worldwide.",
        "skills": "Python, Django, FastAPI, PostgreSQL, Docker, AWS",
        "preferences": "Full-time, Remote, Hybrid",
    }

    # Test data for LinkedIn search configuration
    linkedin_search_config = {
        "positions": ["Software Engineer", "Python Developer", "Backend Developer"],
        "locations": ["Germany", "Remote", "Berlin"],
        "remote": True,
        "hybrid": True,
        "onsite": False,
        "experience_level": {
            "entry": True,
            "associate": True,
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

    print("=== Test: LinkedIn Job Vacancy Data ===")
    print(transform_vacancy_data(linkedin_job_data))
    print("\n" + "=" * 50 + "\n")

    print("=== Test: LinkedIn Search Configuration ===")
    print(transform_search_config_data(linkedin_search_config))
    print("\n" + "=" * 50 + "\n")

    # Test with minimal data
    minimal_job_data = {"job_title": "Developer", "company_name": "Startup Inc"}

    minimal_search_config = {"positions": ["Developer"], "remote": True}

    print("=== Test: Minimal Job Data ===")
    print(transform_vacancy_data(minimal_job_data))
    print("\n" + "=" * 50 + "\n")

    print("=== Test: Minimal Search Config ===")
    print(transform_search_config_data(minimal_search_config))
    print("\n" + "=" * 50 + "\n")

    # Test with empty data
    print("=== Test: Empty Data ===")
    print("Empty job data:", transform_vacancy_data({}))
    print("Empty search config:", transform_search_config_data({}))
    print("None job data:", transform_vacancy_data(None))
    print("None search config:", transform_search_config_data(None))
