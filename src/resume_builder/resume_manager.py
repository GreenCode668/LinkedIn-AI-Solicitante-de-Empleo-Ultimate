import os
import sys
import tempfile
import webbrowser
from pathlib import Path

import inquirer

from config.app_config import RESUME_STYLE
from config.logger_config import logger
from src.utils.browser_utils import HTML_to_PDF


class ResumeManager:
    """Class interface with resume generator"""

    def __init__(self, api_key, style_manager, resume_generator):
        # Get full path to library directory
        lib_directory = Path(__file__).resolve().parent
        styles_directory = lib_directory / "resume_style"
        self.style_manager = style_manager
        self.style_manager.set_styles_directory(styles_directory)
        self.resume_generator = resume_generator
        self.selected_style = None  # property to store selected style

    def prompt_user(self, choices: list[str], message: str) -> str:
        questions = [
            inquirer.List("selection", message=message, choices=choices),
        ]
        return inquirer.prompt(questions)["selection"]

    def is_interactive_mode(self) -> bool:
        """Check if running in interactive mode (TTY available)"""
        return sys.stdin.isatty()

    def choose_default_style(self):
        """Choose default resume style without user interaction (for Docker/headless mode)"""
        styles = self.style_manager.get_styles()
        if not styles:
            logger.warning("No available styles")
            return None

        # Use the first available style (typically FAANGPath which is recommended)
        default_style = list(styles.keys())[0]
        self.selected_style = default_style
        logger.info(f"Non-interactive mode: Using default resume style '{default_style}'")

    def choose_style(self):
        """Choose resume style (interactive or default based on environment)"""
        if RESUME_STYLE is not None:
            self.selected_style = RESUME_STYLE
            logger.info(f"Using resume style from config: '{RESUME_STYLE}'")
            return

        # Check if running in non-interactive mode (Docker, no TTY)
        if not self.is_interactive_mode():
            logger.info("Running in non-interactive mode (Docker/headless)")
            self.choose_default_style()
            return

        # Interactive mode - prompt user
        styles = self.style_manager.get_styles()
        if not styles:
            logger.warning("No available styles")
            return None

        final_style_choice = "Create your own style in CSS"
        formatted_choices = self.style_manager.format_choices(styles)
        formatted_choices.append(final_style_choice)

        try:
            selected_choice = self.prompt_user(
                formatted_choices, "Which resume style would you like to use?"
            )
            if selected_choice == final_style_choice:
                tutorial_url = "https://github.com/feder-cr/lib_resume_builder_AIHawk/blob/main/how_to_contribute/web_designer.md"
                logger.info("\nOpening tutorial in your browser...")
                webbrowser.open(tutorial_url)
                exit()
            else:
                self.selected_style = selected_choice.split(" (")[0]
        except Exception as e:
            logger.warning(f"Could not get interactive input: {e}")
            logger.info("Falling back to default style selection")
            self.choose_default_style()

    async def pdf_base64(self) -> str:
        """Create PDF file from generated HTML template"""
        if self.selected_style is None:
            raise ValueError("Before creating a PDF file, you need to select a style.")

        style_path = self.style_manager.get_style_path(self.selected_style)

        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".html", encoding="utf-8"
        ) as temp_html_file:
            temp_html_path = temp_html_file.name
            self.resume_generator.create_resume(style_path, temp_html_path)

        pdf_base64 = await HTML_to_PDF(temp_html_path)
        os.remove(
            temp_html_path
        )  # Comment this line to keep the HTML file for debugging (is in /tmp directory)
        return pdf_base64


if __name__ == "__main__":
    """Simple test to generate a resume"""
    import asyncio

    import dotenv

    from config.constants import RESUME_DIR
    from src.job_manager.resume_anonymizer import ResumeAnonymizer
    from src.llm.llm_manager import GPTAnswerer
    from src.resume_builder.resume_generator import ResumeGenerator
    from src.resume_builder.style_manager import StyleManager
    from src.utils.utils import load_yaml_file

    async def test_resume_generation():
        """Test resume generation functionality"""
        logger.info("Starting resume generation test...")

        try:
            # Load secrets for LLM
            secrets = dotenv.dotenv_values(".env")
            llm_api_key = secrets.get("llm_api_key", "")
            llm_proxy = secrets.get("llm_proxy", "")

            # Load resume data
            resume_structured_file = Path(RESUME_DIR) / "structured_resume.yaml"
            resume_text_file = Path(RESUME_DIR) / "resume_text.txt"

            # Load structured resume
            resume_structured = load_yaml_file(resume_structured_file)
            # Load resume text
            with open(resume_text_file, "r", encoding="utf-8") as f:
                resume_text = f.read()

            # Set resume anonymizer and anonymize the resume information
            resume_anonymizer = ResumeAnonymizer(resume_structured)
            resume_anonymizer.anonymize_personal_information()
            resume_structured = resume_anonymizer.resume_anonymized
            resume_text = resume_anonymizer.anonymize_text(resume_text)

            # Initialize GPT answerer
            gpt_answerer = GPTAnswerer(llm_api_key, llm_proxy)
            gpt_answerer.set_resume(resume_structured, resume_text)

            # Create a test job for resume generation
            test_job = {
                "job_title": "BrowserUse consultant engineer position",
                "company_name": "Teemo AI",
                "job_description": "We are looking for a BrowserUse consultant engineer with experience in BrowserUse, Chrome Extensions, and cloud technologies.",
            }
            gpt_answerer.set_job(test_job)

            # Initialize style manager and resume generator
            style_manager = StyleManager()
            resume_generator = ResumeGenerator(gpt_answerer, resume_anonymizer)

            # Initialize facade manager
            resume_manager = ResumeManager(llm_api_key, style_manager, resume_generator)
            resume_manager.choose_style()

            # # Choose a style (use first available style)
            # styles = style_manager.get_styles()
            # if styles:
            #     first_style = list(styles.keys())[0]
            #     resume_manager.selected_style = first_style
            #     logger.info(f"Selected style: {first_style}")
            # else:
            #     logger.warning("No styles available, using default")
            #     resume_manager.selected_style = "default"

            # Generate PDF resume
            logger.info("Generating PDF resume...")
            pdf_base64 = await resume_manager.pdf_base64()

            # Save the generated resume to a file for inspection
            output_file = Path("test_generated_resume.pdf")
            import base64

            with open(output_file, "wb") as f:
                f.write(base64.b64decode(pdf_base64))

            logger.info(f"✅ Resume generated successfully! Saved to: {output_file}")
            logger.info(f"PDF size: {len(pdf_base64)} characters")

            return True

        except FileNotFoundError as e:
            logger.error(f"❌ Required file not found: {e}")
            logger.error("Make sure you have:")
            logger.error("1. data/secrets/secrets.yaml with LLM API key")
            logger.error("2. data/resume/resume.txt with your resume text")
            logger.error("3. data/resume/structured_resume.yaml with structured resume data")
            return False

        except Exception as e:
            logger.error(f"❌ Resume generation test failed: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    # Run the test
    success = asyncio.run(test_resume_generation())
    if success:
        print("✅ Resume generation test passed!")
    else:
        print("❌ Resume generation test failed!")
