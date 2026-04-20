from typing import List, Optional

from pydantic import BaseModel, field_validator, model_validator


class ExperienceLevel(BaseModel):
    internship: bool = False
    entry: bool = False
    associate: bool = False
    mid_senior_level: bool = False
    director: bool = False
    executive: bool = False


class JobTypes(BaseModel):
    full_time: bool = False
    contract: bool = False
    part_time: bool = False
    temporary: bool = False
    volunteer: bool = False
    internship: bool = False
    other: bool = False


class DatePosted(BaseModel):
    all_time: bool = False
    month: bool = False
    week: bool = False
    day_24_hours: bool = False

    @model_validator(mode="after")
    def validate_only_one_true(self):
        true_count = sum(
            1
            for flag in (
                self.all_time,
                self.month,
                self.week,
                self.day_24_hours,
            )
            if bool(flag)
        )
        if true_count > 1:
            raise ValueError("Only one of DatePosted fields can be True at a time")
        return self


class SearchConfig(BaseModel):
    # Search criteria
    positions: List[str]

    # Work arrangement options
    remote: Optional[bool] = False
    hybrid: Optional[bool] = False
    onsite: Optional[bool] = False

    # Experience level settings
    experience_level: Optional[ExperienceLevel] = ExperienceLevel()

    # Job type settings
    job_types: Optional[JobTypes] = JobTypes()

    # Date posted settings
    date: Optional[DatePosted] = DatePosted()

    # Location settings
    locations: Optional[List[str]] = []

    # Application settings
    apply_once_at_company: Optional[bool] = True

    # Blacklists
    company_blacklist: Optional[List[str]] = []
    title_blacklist: Optional[List[str]] = []
    location_blacklist: Optional[List[str]] = []


class ConnectionSearcherConfig(BaseModel):
    main_search_words: List[str] = [
        "Open Networker",
        "LION",
        "NO IDK",
    ]
    additional_search_words: List[str] = []


class Secrets(BaseModel):
    linkedin_email: str
    linkedin_password: str
    llm_api_key: Optional[str] = None
    llm_proxy: Optional[str] = None
    llm_api_url: Optional[str] = None
    tg_token: Optional[str] = None
    tg_api_id: Optional[str] = None
    tg_api_hash: Optional[str] = None

    @field_validator("tg_api_id", mode="before")
    @classmethod
    def validate_tg_api_id(cls, v):
        if isinstance(v, int):
            return str(v)
        elif isinstance(v, str):
            return v
        else:
            raise ValueError("tg_api_id must be a string or an integer")
