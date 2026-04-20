import asyncio
import os

import dotenv
import traceback
import yaml
from playwright.async_api import Locator, Page
from config.logger_config import logger
from src.job_manager.authenticator import LinkedInAuthenticator
from src.pydantic_models.config_models import ConnectionSearcherConfig
from src.utils.browser_utils import create_playwright_browser, pause, save_browser_session


class ConnectionSearcher:
    def __init__(self, config_path: str = "config/connection_searcher_config.yaml"):
        self.config = self._load_config(config_path)
        self.secrets = self._load_secrets()
        # Expanded keywords that indicate an open networker
        self.open_networker_keywords = [
            "L.I.O.N",
            "Open Networker",
            "Networking",
            "Accepting Invites",
            "Invites Welcome",
            "I accept all invites",
            "Open to connect",
            "Let's connect",
            "10k+",
            "20k+",
            "30k+",
            "megalion",
            "top lion",
            "fast connect",
            "I never say no",
            "open to networking",
            "send me an invite",
            "no idk",
            "will not idk",
        ]
        self.person_name = ""
        self.found_keywords = []

    def _load_config(self, config_path: str) -> ConnectionSearcherConfig:
        if not os.path.exists(config_path):
            logger.warning(f"Config file {config_path} not found. Using defaults.")
            return ConnectionSearcherConfig()
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
        return ConnectionSearcherConfig(**config_data)

    def _load_secrets(self) -> dict:
        secrets = {**dotenv.dotenv_values(".env")}
        # Basic validation
        if "linkedin_email" not in secrets or "linkedin_password" not in secrets:
            logger.error("LinkedIn credentials not found in .env")
            raise ValueError("Missing LinkedIn credentials in .env")
        return secrets

    async def run(self):
        browser, context, page = await create_playwright_browser()
        try:
            # Login
            authenticator = LinkedInAuthenticator(page)
            authenticator.set_parameters(
                self.secrets["linkedin_email"], self.secrets["linkedin_password"]
            )
            login_success = await authenticator.start()
            if not login_success:
                logger.error("Failed to log into LinkedIn")
                return

            await save_browser_session(context)
            logger.info("Successfully logged into LinkedIn!")

            for main_word in self.config.main_search_words:
                for add_word in self.config.additional_search_words:
                    logger.info(f"Starting search for: {main_word} + {add_word}")
                    pause(4, 8)
                    await self._search_and_connect(page, main_word, add_word)
                    pause(4, 8)
        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(f"Unknown error: {str(e)}\n{tb_str}")
        finally:
            await browser.close()

    async def _search_and_connect(self, page: Page, main_word: str, add_word: str):
        for page_num in range(1, 101):
            logger.info(f"Processing page {page_num} for {main_word} + {add_word}")
            # URL: https://www.linkedin.com/search/results/people/?keywords={main_search_word}+{additional_search_word}
            query = f"{main_word} {add_word}".replace(" ", "+")
            url = (
                f"https://www.linkedin.com/search/results/people/?keywords={query}&page={page_num}"
            )
            await page.goto(url)
            pause(1, 2)  # Allow page to settle

            # Wait for results or empty state with multiple possible selectors
            result_selectors = [
                "div[data-view-name='people-search-result']",
                # "[role='listitem']",
            ]
            combined_selector = ", ".join(result_selectors)

            try:
                await page.wait_for_selector(combined_selector, timeout=5000)
            except Exception as e:
                # If wait fails, check if "No results found" is actually visible
                if await page.get_by_text("No results found").is_visible():
                    logger.info(f"No results found on page {page_num}. Moving to next combination.")
                    break

                # Check if we have any results despite the timeout (sometimes visible state is tricky)
                count = await page.locator(combined_selector).count()
                if count == 0:
                    logger.error(f"Error waiting for results on page {page_num}: {e}")
                    break

            # Scroll down to load all results
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            pause(1, 2)
            await page.evaluate("window.scrollTo(0, 0)")
            pause(1, 2)

            people = await page.locator(combined_selector).all()
            if not people:
                logger.info(
                    f"No people found on page {page_num} after scrolling. Moving to next combination."
                )
                break

            for person in people:
                try:
                    if await self._should_connect(person):
                        await self._connect_with_person(page, person)
                except Exception as e:
                    logger.error(f"Error processing person: {e}")

            # Check for next page button
            next_button = page.locator(
                "button[data-testid='pagination-controls-next-button-visible']"
            )
            if not await next_button.is_visible() or page_num >= 100:
                logger.info("Reached the end of results or 100th page.")
                break
            pause(5, 10)

    async def _should_connect(self, person: Locator) -> bool:
        # Extract elements and analyze description.
        # Skip if keywords are ONLY in mutual connections text.
        full_text = await person.inner_text() or ""
        full_text = " ".join(
            [
                text.strip()
                for text in full_text.split("\n")
                if "is a mutual connection" not in text.strip()
                and "are mutual connections" not in text.strip()
                and "other mutual connection" not in text.strip()
            ]
        )

        found_keywords = [
            kw for kw in self.open_networker_keywords if kw.lower() in full_text.lower()
        ]

        person_name = full_text.split("•")[0].strip() if "•" in full_text else ""

        if found_keywords or "LION" in full_text:
            if "LION" in full_text:
                self.found_keywords = ["LION"]
            else:
                self.found_keywords = found_keywords
            self.person_name = person_name
            return True
        return False

    async def _connect_with_person(self, page: Page, person: Locator):
        # 7. Find Connect button and push it.
        # Specific selector for the 'Invite to connect' button provided in the HTML
        connect_btn = person.locator("a[aria-label^='Invite'][aria-label$='to connect']")

        # If the 'a' tag selector fails, try the internal text as a fallback
        if await connect_btn.count() == 0:
            return

        if await connect_btn.count() > 0 and await connect_btn.first.is_visible():
            logger.info(
                f"Found open networker keywords {self.found_keywords} in person's {self.person_name} description."
            )
            await connect_btn.first.click()
            logger.info("Clicked Connect button.")
            await self._handle_invitation_modal(page)
        else:
            # Check if it's in the 'More' menu as a last resort
            more_btn = person.locator("button:has-text('More')")
            if await more_btn.count() > 0 and await more_btn.first.is_visible():
                await more_btn.first.click()
                pause(1, 2)
                dropdown_connect = page.locator(
                    "div.artdeco-dropdown__content [aria-label^='Invite'][aria-label$='to connect'], div.artdeco-dropdown__content button:has-text('Connect')"
                )
                if await dropdown_connect.count() > 0:
                    await dropdown_connect.first.click()
                    logger.info("Clicked Connect button from More menu.")
                    await self._handle_invitation_modal(page)

    async def _handle_invitation_modal(self, page: Page):
        pause(1, 2)
        # Check for "Add a note to your invitation?" modal
        # 7. Find button with name "Send without a note" and push it.
        send_without_note = page.locator(
            "button[aria-label='Send without a note'], button:has-text('Send without a note')"
        )
        if await send_without_note.count() > 0 and await send_without_note.first.is_visible():
            await send_without_note.first.click()
            logger.info("Sent invitation without a note.")
            pause(1, 2)
        else:
            # Maybe it sent directly or there is a "Send" button
            send_now = page.locator("button:has-text('Send now'), button[aria-label='Send now']")
            if await send_now.count() > 0 and await send_now.first.is_visible():
                await send_now.first.click()
                logger.info("Sent invitation using 'Send now'.")
                pause(1, 2)
        pause(5, 10)


if __name__ == "__main__":
    searcher = ConnectionSearcher()
    asyncio.run(searcher.run())
