from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class Job(BaseModel):
    """
    LinkedIn job posting model with comprehensive validation and metadata.

    This model represents a job posting scraped from LinkedIn with all relevant
    information needed for automated job applications.
    """

    # Core job information
    job_title: str = Field(
        default="",
        description="The title/position name of the job posting",
    )

    company_name: str = Field(default="", description="Name of the company posting the job")

    location: str = Field(default="", description="Job location (city, state, country or remote)")

    url: str = Field(default="", description="Direct URL to the LinkedIn job posting")

    # Job content and requirements
    job_description: str = Field(
        default="",
        description="Full job description including responsibilities and requirements",
    )

    company_description: str = Field(
        default="", description="About the company section from the job posting"
    )

    # Application details
    apply_method: str = Field(
        default="", description="Method of application (Easy Apply, External, etc.)"
    )

    recruiter_link: str = Field(default="", description="Link to the recruiter's LinkedIn profile")

    # Skills and preferences
    skills: str = Field(
        default="",
        description="Required skills and qualifications (comma-separated)",
    )

    preferences: str = Field(
        default="",
        description="Job preferences like work type, salary range, etc.",
    )

    # Additional metadata
    job_id: Optional[str] = Field(default=None, description="LinkedIn job ID extracted from URL")

    posted_date: Optional[datetime] = Field(
        default=None, description="When the job was posted (if available)"
    )

    application_deadline: Optional[datetime] = Field(
        default=None, description="Application deadline (if specified)"
    )

    salary_range: Optional[str] = Field(
        default=None, description="Salary range if mentioned in the posting"
    )

    employment_type: Optional[str] = Field(
        default=None,
        description="Type of employment (Full-time, Part-time, Contract, etc.)",
    )

    experience_level: Optional[str] = Field(
        default=None,
        description="Required experience level (Entry, Mid, Senior, etc.)",
    )

    is_remote: bool = Field(default=False, description="Whether this is a remote position")

    # is_easy_apply: bool = Field(
    #     default=False, description="Whether this job supports LinkedIn Easy Apply"
    # )

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v):
        """Ensure URL is a valid LinkedIn job URL"""
        if not v:
            return v
        if isinstance(v, str):
            if not v.startswith(("http://", "https://")):
                v = f"https://{v}"
            parsed = urlparse(v)
            if "linkedin.com" not in parsed.netloc or "/jobs/view/" not in parsed.path:
                raise ValueError("URL must be a valid LinkedIn job posting URL")
        return v

    @field_validator("job_id", mode="before")
    @classmethod
    def extract_job_id(cls, v, info):
        """Extract job ID from URL if not provided"""
        if v:
            return v
        url = info.data.get("url", "")
        if url and "/jobs/view/" in str(url):
            import re

            match = re.search(r"/jobs/view/(\d+)", str(url))
            if match:
                return match.group(1)
        return None

    @field_validator("is_remote", mode="before")
    @classmethod
    def determine_remote_status(cls, v, info):
        """Determine if job is remote based on location"""
        if v:
            return v
        location = info.data.get("location", "").lower()
        return any(
            keyword in location for keyword in ["remote", "work from home", "wfh", "virtual"]
        )

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v):
        """Clean and normalize skills string"""
        if not v:
            return v
        # Remove extra whitespace and normalize separators
        skills = [skill.strip() for skill in v.split(",") if skill.strip()]
        return ", ".join(skills)

    @field_validator("preferences")
    @classmethod
    def clean_preferences(cls, v):
        """Clean and normalize preferences string"""
        if not v:
            return v
        # Remove extra whitespace and normalize separators
        prefs = [pref.strip() for pref in v.split(",") if pref.strip()]
        return ", ".join(prefs)

    def is_valid_for_application(self) -> bool:
        """Check if job has minimum required information for application"""
        return bool(self.job_title and self.company_name and self.url and self.job_description)

    def get_str_url(self) -> str:
        """Convert URL to serializable string"""
        return str(self.url)


class JobManagerCache(BaseModel):
    """
    Cache model for JobManager to store application statistics and timing information.

    This model represents the cache structure used in JobManager to track
    application progress, timing, and various statistics across sessions.
    """

    # Timing information
    last_run: Optional[str] = Field(
        default=None, description="ISO format timestamp of the last search run"
    )

    last_apply: Optional[str] = Field(
        default=None, description="ISO format timestamp of the last successful application"
    )

    # Application counters
    success_applies_num: int = Field(
        default=0, description="Number of successful applications in current session"
    )

    total_applies_num: int = Field(
        default=0, description="Total number of successful applications across all sessions"
    )

    @field_validator("last_run", "last_apply", mode="before")
    @classmethod
    def validate_timestamp(cls, v):
        """Validate timestamp format"""
        if not v:
            return v
        if isinstance(v, str):
            try:
                datetime.fromisoformat(v)
                return v
            except ValueError:
                raise ValueError("Timestamp must be in ISO format")
        return v

    @field_validator("success_applies_num", "total_applies_num")
    @classmethod
    def validate_positive_counters(cls, v):
        """Ensure counters are non-negative"""
        if v < 0:
            raise ValueError("Counters must be non-negative")
        return v

    def get_last_run_datetime(self) -> Optional[datetime]:
        """Get last_run as datetime object"""
        if self.last_run:
            return datetime.fromisoformat(self.last_run)
        return None

    def get_last_apply_datetime(self) -> Optional[datetime]:
        """Get last_apply as datetime object"""
        if self.last_apply:
            return datetime.fromisoformat(self.last_apply)
        return None

    def update_last_run(self) -> None:
        """Update last_run to current timestamp"""
        self.last_run = datetime.now().isoformat()

    def update_last_apply(self) -> None:
        """Update last_apply to current timestamp"""
        self.last_apply = datetime.now().isoformat()


class JobInfo(BaseModel):
    """
    Company job info model for storing company job information.
    """

    job_title: str = Field(default="", description="Title of the job")
    company_name: Optional[str] = Field(default=None, description="Name of the company")
    url: str = Field(default="", description="URL of the job")
    skip_reason: Optional[str] = Field(
        default="", description="If application was skipped, reason for the skip"
    )
    skills: Optional[List[str]] = Field(default=None, description="Skills required for the job")
    interest_score: Optional[int] = Field(
        default=None, description="Interest score of the job, from 1 to 100"
    )
    interest_reason: Optional[str] = Field(
        default=None, description="Reasoning for the interest score"
    )

    @field_validator("interest_score", mode="before")
    @classmethod
    def validate_interest_score(cls, v):
        """Validate interest score"""
        if isinstance(v, str):
            if not v.isdigit():
                raise ValueError("Interest score must be a number")
            v = int(v)
        if v < 1 or v > 100:
            raise ValueError("Interest score must be between 1 and 100")
        return v


class Question(BaseModel):
    """
    Question model for storing question information.
    """

    question: str = Field(default="", description="Question text")
    question_type: str = Field(default="", description="Type of the question")
    answer: str | List[str] = Field(default="", description="Answer to the question")
