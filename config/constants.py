# Dummy personal data for anonymization (male)
DUMMY_PERSONAL_INFO_MALE = {
    "name": "Zorquill Thalaorix",
    "last_name_2": "Zorquill Thalaorix",
    # "birthday": "03.05.1993",
    "phone": "9335753535",
    "email": "zorquill_thalaorix@gmail.com",
    "linkedin": "https://linkedin.com/in/zorquill_thalaorix-f3e57c712",
    "github": "https://github.com/zorquill_thalaorix",
    "zip_code": "09876",
    "address": "1234 Imaginary Lane",
}

# Dummy personal data for anonymization (female)
DUMMY_PERSONAL_INFO_FEMALE = {
    "name": "Zorquillia Thalaorix",
    "last_name_2": "Zorquillia Thalaorix",
    # "birthday": "03.05.1993",
    "phone": "9335753535",
    "email": "zorquillia_thalaorix@gmail.com",
    "linkedin": "https://linkedin.com/in/zorquillia_thalaorix-f3e57c712",
    "github": "https://github.com/zorquillia_thalaorix",
    "zip_code": "09876",
    "address": "1234 Imaginary Lane",
}

# Paths to log files and settings
SEARCH_CONFIG_FILE = "config/search_config.yaml"
LAST_RUN_FILE = "data/output/last_run.yaml"
ANSWERS_FILE = "data/output/answers.yaml"
OUTPUT_DIR = "data/output"
LOG_DIR = "logs"
RESUME_DIR = "data/resumes"
COVER_LETTER_DIR = "data/cover_letters"
BROWSER_STORAGE_STATE = "browser_session/linkedin_state.json"
APP_CONFIG_FILE = "config/app_config.yaml"

# Default cost per token fallback when model is not in PRICE_DICT
CUSTOM_COST_PER_TOKEN = {
    "input_cost_per_token": 0.25 / 1_000_000,
    "output_cost_per_token": 1.50 / 1_000_000,
}

# Per-model token pricing (input/output cost per token in USD)
PRICE_DICT: dict[str, dict[str, float]] = {
    # Gemini
    "gemini-3.1-flash-lite-preview": {
        "input_cost_per_token": 0.075 / 1_000_000,
        "output_cost_per_token": 0.30 / 1_000_000,
    },
    "gemini-3-flash-preview": {
        "input_cost_per_token": 0.15 / 1_000_000,
        "output_cost_per_token": 0.60 / 1_000_000,
    },
    # OpenAI
    "gpt-4o-mini": {
        "input_cost_per_token": 0.15 / 1_000_000,
        "output_cost_per_token": 0.60 / 1_000_000,
    },
    "gpt-4o": {
        "input_cost_per_token": 2.50 / 1_000_000,
        "output_cost_per_token": 10.00 / 1_000_000,
    },
    "gpt-5-mini": {
        "input_cost_per_token": 0.15 / 1_000_000,
        "output_cost_per_token": 0.60 / 1_000_000,
    },
    "gpt-5-nano": {
        "input_cost_per_token": 0.10 / 1_000_000,
        "output_cost_per_token": 0.40 / 1_000_000,
    },
    # Anthropic
    "anthropic/claude-haiku-4-5": {
        "input_cost_per_token": 0.80 / 1_000_000,
        "output_cost_per_token": 4.00 / 1_000_000,
    },
    "anthropic/claude-sonnet-4": {
        "input_cost_per_token": 3.00 / 1_000_000,
        "output_cost_per_token": 15.00 / 1_000_000,
    },
    "anthropic/claude-sonnet-4-5": {
        "input_cost_per_token": 3.00 / 1_000_000,
        "output_cost_per_token": 15.00 / 1_000_000,
    },
    "anthropic/claude-sonnet-4-6": {
        "input_cost_per_token": 3.00 / 1_000_000,
        "output_cost_per_token": 15.00 / 1_000_000,
    },
}


def cost_per_token(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    custom_cost_per_token: dict | None = None,
) -> tuple[float, float]:
    """Return (prompt_cost, completion_cost) for the given model and token counts."""
    rates = PRICE_DICT.get(model, custom_cost_per_token or CUSTOM_COST_PER_TOKEN)
    return (
        prompt_tokens * rates["input_cost_per_token"],
        completion_tokens * rates["output_cost_per_token"],
    )
