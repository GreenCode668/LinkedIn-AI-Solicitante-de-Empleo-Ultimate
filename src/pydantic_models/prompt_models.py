from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PersonalInfo(BaseModel):
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    gender: str = Field(description="Gender, must be either male or female")
    date_of_birth: Optional[str] = Field(default="No info", description="Date of birth")
    country: Optional[str] = Field(default="No info", description="Country")
    city: Optional[str] = Field(default="No info", description="City")
    state_area_region: Optional[str] = Field(default="No info", description="State/area/region")
    address: Optional[str] = Field(default="No info", description="Address")
    zip_code: Optional[str | int] = Field(default="No info", description="ZIP code")
    phone: Optional[str] = Field(
        default="No info", description="Phone number without country Phone code"
    )
    phone_code: Optional[str] = Field(default="No info", description="Phone code")
    email: Optional[str] = Field(default="No info", description="Email address")
    github: Optional[str] = Field(default="No info", description="GitHub profile URL")
    linkedin: Optional[str] = Field(default="No info", description="LinkedIn profile URL")

    @field_validator("gender", mode="before")
    @classmethod
    def validate_gender(cls, v):
        """Validate Gender"""
        if v.lower() not in ["male", "female"]:
            raise ValueError("Gender must be either male or female")
        return v

    @field_validator("github", mode="before")
    @classmethod
    def validate_github_url(cls, v):
        """Validate GitHub URL"""
        if v is None or v == "No info":
            return v
        if not v.startswith(("http://www.github.com/", "https://www.github.com/")):
            return f"https://www.github.com/{v}"
        return v

    @field_validator("linkedin", mode="before")
    @classmethod
    def validate_linkedin_url(cls, v):
        """Validate LinkedIn URL"""
        if v is None or v == "No info":
            return v
        if not v.startswith(("http://www.linkedin.com/in/", "https://www.linkedin.com/in/")):
            return f"https://www.linkedin.com/in/{v}"
        return v

    @field_validator("zip_code", mode="before")
    @classmethod
    def validate_zip_code(cls, v):
        """Validate ZIP code"""
        if isinstance(v, int):
            return str(v)
        return v


class EducationDetail(BaseModel):
    education_level: Optional[str] = Field(default="No info", description="Education level")
    institution: Optional[str] = Field(default="No info", description="Institution name")
    field_of_study: Optional[str] = Field(default="No info", description="Field of study")
    final_evaluation_grade: Optional[str | int | float] = Field(
        default="No info", description="Final grade, must be a number"
    )
    start_date: Optional[str | int | float] = Field(
        default="No info", description="Start date, must be a number"
    )
    year_of_completion: Optional[str | int | float] = Field(
        default="No info", description="Completion year, must be a number"
    )
    exam: Optional[Dict[str, str] | str] = Field(
        default="No info", description="Exam grades, must be a dictionary or a string"
    )
    location: Optional[str] = Field(default="No info", description="Location")


class ExperienceDetail(BaseModel):
    position: Optional[str] = Field(default="No info", description="Job position")
    company: Optional[str] = Field(default="No info", description="Company name")
    employment_period: Optional[str] = Field(default="No info", description="Employment period")
    location: Optional[str] = Field(default="No info", description="Location")
    industry: Optional[str] = Field(default="No info", description="Industry")
    key_responsibilities: Optional[List[str]] = Field(
        default_factory=list, description="List of key responsibilities"
    )
    skills_acquired: Optional[List[str]] = Field(
        default_factory=list, description="Skills acquired"
    )


class Project(BaseModel):
    name: Optional[str] = Field(default="No info", description="Project name")
    description: Optional[str] = Field(default="No info", description="Project description")
    link: Optional[str] = Field(default="No info", description="Project link")


class Achievement(BaseModel):
    name: Optional[str] = Field(default="No info", description="Achievement name")
    description: Optional[str] = Field(default="No info", description="Achievement description")


class Certification(BaseModel):
    name: Optional[str] = Field(default="No info", description="Certification name")
    description: Optional[str] = Field(default="No info", description="Certification description")


class Language(BaseModel):
    language: Optional[str] = Field(default="No info", description="Language name")
    proficiency: Optional[str] = Field(default="No info", description="Proficiency level")


class Availability(BaseModel):
    notice_period: Optional[str] = Field(default="No info", description="Notice period")


class SalaryExpectations(BaseModel):
    salary_range_usd: Optional[str] = Field(default="No info", description="Salary range in USD")


class SelfIdentification(BaseModel):
    pronouns: Optional[str] = Field(default="No info", description="Pronouns")
    veteran: Optional[str | bool] = Field(default="No info", description="Veteran status")
    disability: Optional[str | bool] = Field(default="No info", description="Disability status")
    race: Optional[str] = Field(default="No info", description="Race")
    ethnicity: Optional[str] = Field(default="No info", description="Ethnicity")


class LegalAuthorization(BaseModel):
    eu_work_authorization: Optional[str | bool] = Field(
        default="No info", description="EU work authorization"
    )
    us_work_authorization: Optional[str | bool] = Field(
        default="No info", description="US work authorization"
    )
    requires_us_visa: Optional[str | bool] = Field(
        default="No info", description="Requires US visa"
    )
    requires_us_sponsorship: Optional[str | bool] = Field(
        default="No info", description="Requires US sponsorship"
    )
    requires_eu_visa: Optional[str | bool] = Field(
        default="No info", description="Requires EU visa"
    )
    legally_allowed_to_work_in_eu: Optional[str] = Field(
        default="No info", description="Legally allowed to work in EU"
    )
    legally_allowed_to_work_in_us: Optional[str | bool] = Field(
        default="No info", description="Legally allowed to work in US"
    )
    requires_eu_sponsorship: Optional[str | bool] = Field(
        default="No info", description="Requires EU sponsorship"
    )
    canada_work_authorization: Optional[str | bool] = Field(
        default="No info", description="Canada work authorization"
    )
    requires_canada_visa: Optional[str | bool] = Field(
        default="No info", description="Requires Canada visa"
    )
    legally_allowed_to_work_in_canada: Optional[str | bool] = Field(
        default="No info", description="Legally allowed to work in Canada"
    )
    requires_canada_sponsorship: Optional[str | bool] = Field(
        default="No info", description="Requires Canada sponsorship"
    )
    uk_work_authorization: Optional[str | bool] = Field(
        default="No info", description="UK work authorization"
    )
    requires_uk_visa: Optional[str | bool] = Field(
        default="No info", description="Requires UK visa"
    )
    legally_allowed_to_work_in_uk: Optional[str | bool] = Field(
        default="No info", description="Legally allowed to work in UK"
    )
    requires_uk_sponsorship: Optional[str | bool] = Field(
        default="No info", description="Requires UK sponsorship"
    )


class WorkPreferences(BaseModel):
    remote_work: Optional[str | bool] = Field(
        default="No info", description="Remote work preference"
    )
    in_person_work: Optional[str] = Field(
        default="No info", description="In-person work preference"
    )
    open_to_relocation: Optional[str | bool] = Field(
        default="No info", description="Open to relocation"
    )
    willing_to_complete_assessments: Optional[str | bool] = Field(
        default="No info", description="Willing to complete assessments"
    )
    willing_to_undergo_drug_tests: Optional[str | bool] = Field(
        default="No info", description="Willing to undergo drug tests"
    )
    willing_to_undergo_background_checks: Optional[str | bool] = Field(
        default="No info", description="Willing to undergo background checks"
    )


class ResumeStructure(BaseModel):
    """Structured resume data model matching structured_resume_template.yaml"""

    personal_information: PersonalInfo = Field(
        default_factory=PersonalInfo, description="Personal information"
    )
    education_details: List[EducationDetail] = Field(
        default_factory=list, description="Education details"
    )
    experience_details: List[ExperienceDetail] = Field(
        default_factory=list, description="Work experience details"
    )
    projects: List[Project] = Field(default_factory=list, description="Projects")
    achievements: List[Achievement] = Field(default_factory=list, description="Achievements")
    certifications: List[Certification] = Field(default_factory=list, description="Certifications")
    languages: List[Language] = Field(default_factory=list, description="Languages")
    interests: List[str] = Field(default_factory=list, description="Interests")
    skills: List[str] = Field(default_factory=list, description="Skills")
    availability: Availability = Field(
        default_factory=Availability, description="Availability information"
    )
    salary_expectations: SalaryExpectations = Field(
        default_factory=SalaryExpectations, description="Salary expectations"
    )
    self_identification: SelfIdentification = Field(
        default_factory=SelfIdentification, description="Self identification"
    )
    legal_authorization: LegalAuthorization = Field(
        default_factory=LegalAuthorization, description="Legal work authorization"
    )
    work_preferences: WorkPreferences = Field(
        default_factory=WorkPreferences, description="Work preferences"
    )
