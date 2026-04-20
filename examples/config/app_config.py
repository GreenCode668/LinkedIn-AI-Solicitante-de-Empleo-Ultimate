"""This file contains application settings"""

"""Maximum number of applications"""
MAX_APPLIES_NUM = 50

"""
If this mode is activated - the browser will be launched in headless mode
"""
HEADLESS_MODE = False

"""
If this mode is activated - apply to all vacancies indiscriminately,
otherwise ask LLM to select only those vacancies that suit you
by interests or by tech stack
"""
MONKEY_MODE = True

"""
In this mode app doesn't apply to the jobs, only creates resumes, cover letters and gathers skill statistics
- resumes are created in data/resume
- cover letters are created in data/output/cover_letters
- skill statistics are gathered in data/output/skill_stat.yaml
"""
TEST_MODE = False

"""
In this mode app doesn't apply to the jobs or create resumes and cover letters, only gathers information for interesting jobs and
their skill statistics and saves them to the files data/output/interesting_jobs.yaml and data/output/skill_stat.yaml."""
COLLECT_INFO_MODE = False

"""
In this mode app applies only the jobs with Easy Apply
If this mode is deactivated, app will apply to the jobs with Easy Apply and try to apply to the jobs with 3rd party applications
WARNING: applying to the jobs with 3rd party applications is not guaranteed to be successful, but is guaranteed to consume at least 10-100x more tokens
"""
EASY_APPLY_ONLY_MODE = True

"""
If this mode is activated, app will check if the last search was less than a day ago.
This is useful if you want bot to automatically restart the search every 24 hours when LinkedIn resets the search limits.
"""
RESTART_EVERY_DAY = False

"""
If LLM evaluated the 'interest' level of the job not below this threshold - the job is considered interesting for application.
Otherwise not.
"""
JOB_IS_INTERESTING_THRESH = 70

"""Minimum time spent on one job application"""
MINIMUM_WAIT_TIME_SEC = 10

"""
If this mode is activated, app will try to decrease RPM to avoid rate limit errors
"""
FREE_TIER = False

"""
Free tier mode wait time in seconds
"""
FREE_TIER_RPM_LIMIT = 15

"""
Logging level
Possible values:
    - "DEBUG"
    - "INFO"
    - "WARNING"
    - "ERROR"
    - "CRITICAL"
"""
MINIMUM_LOG_LEVEL = "DEBUG"

"""
LLM type
Possible values:
    - "openai"
    - "gigachat"
    - "claude"
    - "ollama"
    - "gemini"
    - "huggingface"
"""
LLM_MODEL_TYPE = "openrouter"
# LLM_MODEL_TYPE = "openai"

# LLM models
EASY_APPLY_MODEL = "google/gemini-3.1-flash-lite-preview"
# EASY_APPLY_MODEL = "gpt-5-mini"
APPLY_AGENT_MODEL = "google/gemini-3.1-flash-lite-preview"
# APPLY_AGENT_MODEL = "gpt-5-mini"

"""
Easy Apply model temperature
the higher it is, the more creative the model, but hallucinations may occur
the lower it is, the more strictly the model follows the prompt and invents less
"""
TEMPERATURE = 0.4

"""
Resume style to use for generated resumes.
If set - skips the interactive style selection prompt.
If None - prompts user to select a style interactively.
Possible values:
    - "FAANGPath"
    - "Cloyola Grey"
    - "Modern Blue"
    - "Modern Grey"
    - "Default"
    - "Clean Blue"
"""
RESUME_STYLE = None
