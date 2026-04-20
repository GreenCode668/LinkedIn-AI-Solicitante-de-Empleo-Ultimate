# LinkedIn AI Job Applier Ultimate

## 🤖 Introduction

**LinkedIn AI Job Applier Ultimate** is an intelligent, AI-powered bot that transforms the way you search for jobs on LinkedIn. Instead of spending countless hours scrolling through listings, tweaking your resume for each role, and answering the same application questions over and over, this bot does it all for you — automatically, thoughtfully, and at scale.

Powered by modern large language models, the bot reads your resume, understands your experience, and applies to jobs that genuinely match your profile. For every vacancy, it crafts a tailored resume and cover letter, answers recruiter questions intelligently, and even expands your professional network by connecting with open networkers in your field. Along the way, it gathers valuable insights about the skills employers are looking for and delivers detailed daily reports straight to your Telegram chat.

Whether you're actively hunting for your next role, passively exploring the market, or analyzing which skills are trending in your industry, this bot is designed to be your tireless job-search companion — working around the clock so you don't have to.

### ✨ What Makes It Special

- **🌐 Universal Job Applications** — Applies to *every* job, not just Easy Apply listings, thanks to an integrated browser automation agent.
- **🎯 Tailored Resumes** — Generates a custom resume for each vacancy, adapting skills, experience, and achievements to match the job description perfectly.
- **🔒 Privacy-First Design** — Anonymizes your personal data before sending anything to the LLM, replacing sensitive details with mock information.
- **🎭 Modern Browser Automation** — Built on Playwright for faster, more reliable, and more secure interaction with LinkedIn.
- **🖥️ Headless Mode** — Run it quietly in the background while you use your computer, or deploy it on a server.
- **⏸️ Pause and Resume** — Take full control with a simple `Ctrl+X` to pause and resume at any time.
- **📊 Skill Statistics** — Discover the most in-demand skills in your target roles and use the data to sharpen your resume.
- **🧠 Smart Error Recovery** — Automatically detects and fixes incorrectly filled form fields.
- **🤝 Automated Networking** — Finds and connects with "Open Networkers" (LIONs) to grow your professional network.
- **☑️ Intelligent Form Handling** — Context-aware answers to checkboxes, follow-up questions, and conditional prompts.
- **🤖 AI Resume Parsing** — Automatically converts your plain-text resume into a structured format.
- **📄 Professional Resume Templates** — Including the modern, clean FAANGPath style.
- **📲 Telegram Reports** — Detailed daily summaries and real-time error notifications delivered to your chat.
- **💡 Resume Recommendations** — AI-generated feedback to continuously improve your resume.
- **🌐 Proxy Support** — Works with proxies for all supported LLM providers.
- **🏗️ Robust & Validated** — Pydantic-powered configuration validation catches errors before they become problems.
- **🚀 Flexible LLM Options** — Supports Gemini, OpenAI, OpenRouter, Claude, and local Ollama models. Many work completely free on the free tier.
- **🔐 Secure Credentials** — All secrets safely stored in a `.env` file.
- **🕒 Automated Scheduling** — Built-in 24-hour timer means you can truly "set it and forget it."

---

## 🚀 Getting Started

### Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.12**
- **Git**
- **uv** (optional, but recommended for much faster installation)

### Installation

You can install the bot either locally or via Docker. Choose whichever suits your setup.

#### Option 1: Local Installation

**Step 1 — Clone the repository**

```bash
git clone 
cd LinkedIn-AI-Job-Applier-Ultimate
```

**Step 2 — Install dependencies**

```bash
uv sync
```

**Step 3 — Install the Chromium browser for Playwright**

```bash
playwright install chromium
```

#### Option 2: Docker Installation

**Step 1 — Clone the repository**

```bash
git clone 
cd LinkedIn-AI-Job-Applier-Ultimate
```

**Step 2 — Build the Docker image**

```bash
docker build -t linkedin .
```

**Step 3 — Run the container**

```bash
docker run -v $(pwd)/data:/app/data \
           -v $(pwd)/browser_session:/app/browser_session \
           -v $(pwd)/logs:/app/logs \
           linkedin
```

> ⚠️ **Important Docker Notes:**
> - You **must** set `HEADLESS_MODE = True` in `config/app_config.py` — Docker containers don't have a graphical interface.
> - The **Ctrl+X pause/resume feature will not work** inside Docker (it requires a keyboard listener tied to an X server).
> - **Resume style selection runs automatically** — the bot falls back to the default style (FAANGPath) instead of prompting interactively.

---

## 🔧 Configuration

The bot is configured through a handful of files. Each is described below.

### 1. Secrets (`.env` file)

Create your `.env` file by copying the example:

```bash
cp .env_example .env
```

Then fill in the required values:

```env
# Your LinkedIn credentials
linkedin_email="your_linkedin_email@example.com"
linkedin_password="your_linkedin_password"

# Your LLM API key (e.g. for Gemini)
llm_api_key="your_llm_api_key"

# Optional proxy for LLM requests
llm_proxy="http://your_proxy_url:port"

# Telegram bot token (optional)
tg_token="your_telegram_bot_token"

# Your Telegram chat address, e.g. "@name_of_your_chat"
tg_chat_id="@name_of_your_chat"

# Topic ID for error messages (the number before the last slash in the topic link)
tg_err_topic_id="[ID of error topic]"

# Topic ID for daily application reports
tg_report_topic_id="[ID of report topic]"
```

Telegram settings are optional. Omit them and the bot will still run perfectly — you just won't receive reports or error notifications via Telegram.

### 2. Job Search Parameters (`config/search_config.yaml`)

Copy the example file from `examples/config/search_config.yaml` into `config/` and customize your search. You can define job titles, locations, experience levels, and more:

```yaml
# Example: Mid-Senior level remote software engineer roles
positions:           # the only mandatory setting
  - Software engineer

remote: true
hybrid: false
onsite: false

experience_level:
  mid_senior_level: true
```

### 3. Application Settings (`config/app_config.py`)

Copy this file from `examples/config/app_config.py` and tune the bot's behavior. The most important settings:

- **`MAX_APPLIES_NUM`** — Maximum number of jobs to apply for in a single run.
- **`HEADLESS_MODE`** — Run the browser invisibly. Faster, and lets you use your computer while the bot works.
- **`MONKEY_MODE`** — If `True`, applies to every job found. If `False`, the LLM picks only the best matches.
- **`TEST_MODE`** — If `True`, the bot generates resumes and cover letters but doesn't actually submit anything.
- **`COLLECT_INFO_MODE`** — If `True`, the bot only gathers information and skill statistics without applying or generating resumes. Output goes to `data/output/interesting_jobs.yaml` and `data/output/skill_stat.yaml`.
- **`EASY_APPLY_ONLY_MODE`** — If `True`, applies only to Easy Apply vacancies. Otherwise, the bot will also attempt 3rd-party application forms. ⚠️ 3rd-party applications are not guaranteed to succeed and consume **10×–100× more tokens**.
- **`RESTART_EVERY_DAY`** — If `True`, the bot automatically restarts every 24 hours when LinkedIn resets its daily application limit. Set it and forget it.
- **`JOB_IS_INTERESTING_THRESH`** — The LLM scores job "interest" from 1 to 100. Jobs at or above this threshold get applied to. LinkedIn caps applications at ~50 per day, so a value of **70+** is recommended to ensure you're only applying to great matches.
- **`MINIMUM_WAIT_TIME_SEC`** — Minimum time spent per application. Helps avoid rate-based bans.
- **`FREE_TIER`** — If `True`, the bot reduces its request rate to stay within free-tier limits.
- **`FREE_TIER_RPM_LIMIT`** — Target requests-per-minute limit for free-tier usage.
- **`LLM_MODEL_TYPE`** — Your LLM provider (e.g., `"gemini"`).
- **`EASY_APPLY_MODEL`** — The specific model for Easy Apply vacancies (e.g., `"gemini-2.0-flash"`).
- **`APPLY_AGENT_MODEL`** — The agent model for Non-Easy Apply vacancies (e.g., `"gemini-2.5-flash"`).
- **`RESUME_STYLE`** — Resume style to use. If `None`, you'll be prompted to choose (or the default is used in headless/Docker mode). Available styles: `"FAANGPath"`, `"Cloyola Grey"`, `"Modern Blue"`, `"Modern Grey"`, `"Default"`, `"Clean Blue"`.

#### Supported LLM Providers

The bot supports several LLM providers. Configure via `LLM_MODEL_TYPE` and `EASY_APPLY_MODEL`.

- **Gemini (Google)** — `LLM_MODEL_TYPE = "gemini"` — e.g., `gemini-3.1-flash-lite`, `gemini-3.1-flash`.
- **OpenAI** — `LLM_MODEL_TYPE = "openai"` — e.g., `gpt-4o`, `gpt-4o-mini`.
- **OpenRouter** — `LLM_MODEL_TYPE = "openrouter"` — e.g., `google/gemini-3.1-flash-lite`, `openai/gpt-4o-mini`.
- **Claude (Anthropic)** — `LLM_MODEL_TYPE = "claude"` — e.g., `claude-3-5-sonnet`, `claude-4-opus`.
- **Ollama (local/server)** — `LLM_MODEL_TYPE = "ollama"` — any model you've loaded, e.g., `llama3`, `qwen2.5`.

**Recommendations:** The best balance of speed, quality, and cost is usually **Gemini + gemini-3.1-flash-lite** or **OpenAI + gpt-5-mini**. Gemini is often free on the free tier. Provide your key via `llm_api_key` in `.env`, and optionally set `llm_proxy`.

### 4. Connection Searcher Settings (`config/connection_searcher_config.yaml`)

Copy this file from `examples/config/connection_searcher_config.yaml` to tune the automated networking tool:

- **`main_search_words`** — Keywords like `"Open Networker"` or `"LION"` used to identify networking-friendly profiles.
- **`additional_search_words`** — Narrower keywords for your field (e.g., `"ai"`, `"ml"`, `"data science"`).

The bot tries every combination of these keywords and sends connection requests to profiles that are genuinely open networkers — while intelligently skipping profiles where the keywords only appear in "mutual connections."

### 5. Resume Files (`data/resumes/resume_text.txt` and `data/resumes/structured_resume.yaml`)

Your resume text **must** include your first name, last name, and gender — these are required for anonymization to work correctly.

The bot uses two resume files:

- **`resume_text.txt`** (**mandatory**) — A plain-text file containing everything about your resume. The bot uses this to answer questions and write cover letters. **Tip:** include as much detail as possible. The more context, the better the answers and the more tailored the resumes.
- **`structured_resume.yaml`** — A structured version used for resume generation.

You have two options for the structured file:

- **Automatic Parsing (recommended)** — On the first run, the bot uses the LLM to parse `resume_text.txt` into `structured_resume.yaml` automatically. Just provide the text file and let the bot handle the rest.
- **Manual Creation** — Fill out `structured_resume.yaml` by hand if you prefer. This is useful if you don't want your full resume text sent to an LLM. Note: Automatic Parsing and Non-Easy Apply applications are the *only* bot functions that transmit non-anonymized personal data to the LLM.

Example files live in the `examples/data/resumes` folder.

### 6. Resume Generation

Two options again:

- **Automatic Creation (recommended)** — Leave `data/resumes/` empty and the bot will generate a unique, tailored resume for every vacancy it applies to. Generated resumes are stored in `data/resumes/generated_resumes/`. Sections that don't change between applications (e.g., header) are generated once and cached in `data/resumes/templates/<section_name>.html`. If any section looks wrong, just delete its template file and the LLM will regenerate it.
- **Ready-Made Resume** — Drop your existing PDF resume into `data/resumes/` and the bot will use it as-is. If multiple PDFs are present, the first one found is used.

#### Testing Resume Generation

It's strongly recommended to test the resume generator before running the full bot:

1. Fill out `data/resumes/resume_text.txt` with your resume details.
2. Run the bot once to auto-create `data/resumes/structured_resume.yaml`, or create it manually.
3. Run the generator:

   ```bash
   python src/resume_builder/resume_manager.py
   ```

4. Select a style (FAANGPath is recommended).
5. Check the output file: `test_generated_resume.pdf` in the root directory.
6. Read the generated resume carefully. If you see **No info**, **N/A**, or **None** anywhere, that means information is missing from your source files — add it and regenerate.
7. Once you're happy with the result, rename the file to `resume.pdf` and move it to `data/resumes/`. The bot will use it by default.

---

## ▶️ Usage

Once installation and configuration are complete, you can run the bot with a single command:

```bash
uv run python main.py
```

If any fields in your `structured_resume.yaml` are missing, the bot will show a warning listing the missing fields and offer two choices:

- Press **`y`** to continue anyway.
- Press **`n`** to stop, review what's missing, update `resume_text.txt`, delete `structured_resume.yaml`, and restart. Alternatively, fill in the missing fields manually if you prefer not to let the LLM regenerate the file.

If 30 seconds pass without input, or all fields are already filled, the bot will proceed automatically.

The bot logs its progress to the console and writes detailed log files to the `logs/` directory. When it finishes a run, it sends a summary report to your configured Telegram chat.

### Pause and Resume

If you notice the bot behaving oddly, press **`Ctrl+X`** to pause it. Press **`Ctrl+X`** again to resume. The bot won't stop instantly — give it a couple of seconds to reach a safe pause point.

### Output Files (`data/output/`)

- **`answers.yaml`** — Previously given answers to LinkedIn application questions, reused across runs to minimize LLM calls.
- **`failed.yaml`** — Jobs where an application attempt failed, with reasons.
- **`interesting_jobs.yaml`** — Jobs flagged as interesting by the LLM, with interest scores, reasoning, and extracted key skills, sorted by interest score.
- **`last_run.yaml`** — Internal cache with timestamps and counters used for 24-hour scheduling.
- **`resume_recommendations.txt`** — AI-generated suggestions for improving your resume (generated once and reused unless deleted).
- **`skill_stat.yaml`** — Aggregated statistics of the most frequently requested skills across job descriptions, sorted by frequency.
- **`skipped.yaml`** — Jobs the bot intentionally skipped (blacklist, missing info, not interesting), with reasons.
- **`success.yaml`** — Jobs the bot successfully applied to, with basic info.

### Automated Networking

To run the networking tool separately:

```bash
python connection_searcher.py
```

It will use `config/connection_searcher_config.yaml` to find and connect with open networkers on LinkedIn.

---

## 💵 Application Cost

### Easy Apply Vacancies

For each application, the LLM:

- Decides whether the job is interesting.
- Extracts the key required skills.
- Generates a tailored resume (if needed).
- Writes a cover letter (if needed).
- Answers recruiter questions (anywhere from 1 to 20+).

Typical token usage:

- **Input tokens:** 5,000–15,000
- **Output tokens:** 100–5,000

With the default model (`gemini-2.0-flash`), that's roughly **$0.0005–$0.0035 per application** — basically pocket change. On the free tier, it costs nothing at all (though you may hit quota limits — see Troubleshooting below).

### Non-Easy Apply Vacancies

These use an agentic flow:

- The LLM inspects the page (HTML or screenshots).
- It performs clicks, scrolls, typing, and selections in the browser to complete the application.

This consumes **10×–100× more tokens** than Easy Apply. Only enable this mode if you understand the cost and can afford it.

> **Note:** If the agent hits a registration form on a 3rd-party application site, it will register using your `linkedin_email` as the login and `<email_prefix>_123456` as the password (e.g., `john.doe@gmail.com` → password `john.doe_123456`).

---

## ✅ Running Tests

First, install the dev dependencies:

```bash
# With pip
pip install -r requirements.txt -e ".[dev]"

# With uv
uv sync --dev
```

Then run the test suite from the project root:

```bash
pytest
```

---

## 🐞 Troubleshooting

### 1. LLM API Rate Limit Errors

**Issue:** Errors like `ResourceExhausted: 429 You exceeded your current quota...`

**Fix:**

- Increase `MINIMUM_WAIT_TIME_SEC` in `config/app_config.py` to 15–30 seconds.
- Upgrade from the free plan to a paid plan.

### 2. Incorrect Information in Applications

**Issue:** Wrong data shown for experience, salary, or notice period.

**Fix:**

- Update the prompts in `src/llm/prompts.py` for more specific professional experience guidance.
- Add dedicated fields in `structured_resume.yaml` for experience, expected salary, and notice period.

### 3. YAML Configuration Errors

**Error:** `yaml.scanner.ScannerError: while scanning a simple key`

**If the error is in `structured_resume.yaml`:** Delete it and restart the bot. It will regenerate a correct version from `resume_text.txt`.

**If the error is in `search_config.yaml`:**

- Copy the example from `examples/config/` to `config/` and modify it gradually.
- Check indentation and spacing.
- Use a YAML validator.
- Avoid unnecessary special characters or quotes.

### 4. Bot Logs In But Doesn't Apply

**Issue:** Bot doesn't start, or starts but applies to nothing.

**Fix:**

- Delete `data/output/last_run.yaml` if it exists. It tracks the 24-hour scheduling window, and if the previous run was too recent, the bot will simply wait.
- Check for LinkedIn security checks or CAPTCHAs.
- Verify your `search_config.yaml` parameters.
- Confirm there are actually jobs matching your criteria on LinkedIn.
- Make sure your LinkedIn profile meets the job requirements.
- Review console output for errors.

### General Tips

- Always use the latest version of the bot.
- Verify all dependencies are installed and up to date.
- Check your internet connection.
- Clear browser cache and cookies by deleting everything in the `browser_session/` folder.
- Some LinkedIn Premium users see a different UI, which can confuse the bot. If you hit parsing errors, try using a non-Premium account.

---

## 📨 Telegram Setup

1. Create a Telegram bot and obtain its token. Set `tg_token` in your `.env`.
2. Create a Telegram group with topics enabled.
3. Make the group public (Group Name → Edit → Group Type → Public).
4. Set a permanent link for the group, e.g., `t.me/linkedin_bot_feedback`.
5. Set `TG_CHAT_ID` in `config/app_config.py` to that link, e.g., `TG_CHAT_ID = "@linkedin_bot_feedback"`.
6. Create two topics in the group: one for errors, one for reports.
7. Post a message in each topic. Right-click → *Copy Message Link*. You'll get something like `t.me/c/194xxxx987/11/13`, where `11` is the topic ID. Set `TG_ERR_TOPIC_ID` and `TG_REPORT_TOPIC_ID` accordingly in `config/app_config.py`.

---

## 🤝 Contributing

Contributions are welcome! If you have ideas for improvements or have found a bug, feel free to open an issue or submit a pull request.

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 🙏 Acknowledgements

This project is a fork of and builds upon the excellent work of the original Jobs Applier AI Agent AIHawk project. Non-Easy Apply vacancies are handled with the help of the browser-use library. The LLM system instructions were adapted from community-contributed ChatGPT custom instructions. The FAANGPath resume style is based on a popular Overleaf template.

If you find this project useful, please star ⭐ the repository!
