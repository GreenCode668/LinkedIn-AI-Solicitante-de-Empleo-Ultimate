"""
This module is used to customize the search parameters for the LinkedIn jobs search.
"""

from typing import Any, Dict, Union

from playwright.sync_api import Page

from config.app_config import EASY_APPLY_ONLY_MODE
from config.logger_config import logger

# Import Playwright utilities for enhanced functionality
from src.utils.browser_utils import find_element_safely, safe_click, safe_fill
from src.utils.utils import pause


class SearchCustomizer:
    def __init__(self, page: Union[Page, Any]):
        self.page = page
        self.search_params = {}

        logger.info("SearchCustomizer initialized")

    def set_advanced_search_params(self, parameters: Dict[str, Any]) -> None:
        """Set search parameters"""
        logger.info("Setting SearchCustomizer parameters")
        # loading optional parameters
        self.positions = parameters["positions"]
        self.remote = parameters.get("remote", False)
        self.onsite = parameters.get("onsite", False)
        self.hybrid = parameters.get("hybrid", False)
        self.experience_level = parameters.get("experience_level", {})
        self.job_types = parameters.get("job_types", {})
        self.date_posted = parameters.get("date", {})
        self.locations = parameters.get("locations", [])
        self.apply_once_at_company = parameters.get("apply_once_at_company", True)
        self.company_blacklist = parameters.get("company_blacklist", [])
        self.title_blacklist = parameters.get("title_blacklist", [])
        self.location_blacklist = parameters.get("location_blacklist", [])
        logger.info("SearchCustomizer parameters successfully set")

    async def _set_basic_search_terms(self):
        """Set basic search parameters (keywords and location) - async"""
        try:
            # Set job title/keywords
            if self.positions:
                keyword_selectors = [
                    "input[aria-label*='or company']:not([disabled]):not([aria-hidden='true'])",
                    "input[aria-label*='Search by title']:not([disabled]):not([aria-hidden='true'])",
                    "#jobs-search-box-keyword-id-ember:not([disabled])",
                    ".jobs-search-box__input--keyword:not([disabled])",
                    "input[role='combobox'][aria-label*='Search by title']:not([disabled])",
                ]

                keywords_filled = False
                for selector in keyword_selectors:
                    if await safe_fill(
                        self.page, selector, ", ".join(self.positions), wait_for_timeout=2000
                    ):
                        logger.info(f"Keywords set: {', '.join(self.positions)}")
                        keywords_filled = True
                        pause(1, 2)
                        break

                if not keywords_filled:
                    logger.warning("Could not find or fill keywords field")

            # Set location
            if self.locations:
                location_selectors = [
                    "input[aria-label*='or zip code']:not([disabled]):not([aria-hidden='true'])",
                    "input[aria-label*='City, state']:not([disabled]):not([aria-hidden='true'])",
                    "#jobs-search-box-location-id-ember:not([disabled])",
                    ".jobs-search-box__input--location:not([disabled])",
                    "input[aria-label*='location']:not([disabled]):not([aria-hidden='true'])",
                ]

                location_filled = False
                for selector in location_selectors:
                    if await safe_fill(
                        self.page, selector, ", ".join(self.locations), wait_for_timeout=2000
                    ):
                        logger.info(f"Location set: {', '.join(self.locations)}")
                        pause()

                        # Try to press Enter to apply location
                        element = await find_element_safely(self.page, selector)
                        if element:
                            await self.page.keyboard.press("Enter")

                        location_filled = True
                        break

                if not location_filled:
                    logger.warning("Could not find or fill location field")

                pause()

        except Exception as e:
            logger.error(f"Error setting basic search parameters: {e}")

    async def _open_all_filters(self):
        """Open 'All filters' modal window (async)"""
        try:
            filters_selectors = [
                "//button[contains(., 'All filters')]",
                "button[aria-label*='All filters']",
                "button[aria-label*='Show all filters']",
                ".jobs-search-results-list__filter-button[aria-label*='filters']",
            ]

            for selector in filters_selectors:
                if await safe_click(self.page, selector):
                    pause()
                    logger.info("Filters modal window opened")
                    return True

            logger.warning("Could not find or click All filters button")
            return False
        except Exception as e:
            logger.error(f"Failed to open filters: {e}")
        return False

    async def _set_date_posted_filter(self):
        """Set date posted filter (async)"""
        if not self.date_posted:
            return

        try:
            date_mapping = {
                "24_hours": "Past 24 hours",
                "week": "Past week",
                "month": "Past month",
                "all_time": "Any time",
            }

            for date_key, is_enabled in self.date_posted.items():
                if is_enabled and date_key in date_mapping:
                    date_text = date_mapping[date_key]

                    # Try multiple selector approaches
                    date_selectors = [
                        f"//label[contains(., '{date_text}')]",
                        f"//input[@value='{date_text}']/..",
                        f"label:has-text('{date_text}')",
                        f"[data-test-date-posted-filter-option='{date_key}']",
                    ]

                    date_set = False
                    for selector in date_selectors:
                        if await safe_click(self.page, selector):
                            logger.info(f"Date filter set: {date_text}")
                            date_set = True
                            break

                    if not date_set:
                        logger.warning(f"Could not set date filter: {date_text}")

                    pause()
                    break

        except Exception as e:
            logger.error(f"Error setting date filter: {e}")

    async def _set_experience_level_filter(self):
        """Set experience level filter (async)"""
        if not self.experience_level:
            return

        try:
            experience_mapping = {
                "internship": "Internship",
                "entry": "Entry level",
                "associate": "Associate",
                "mid_senior_level": "Mid-Senior level",
                "director": "Director",
                "executive": "Executive",
            }

            for exp_key, is_enabled in self.experience_level.items():
                if is_enabled and exp_key in experience_mapping:
                    exp_text = experience_mapping[exp_key]

                    # Try multiple selector approaches
                    exp_selectors = [
                        f"//label[contains(., '{exp_text}')]",
                        f"//input[@value='{exp_text}']/..",
                        f"label:has-text('{exp_text}')",
                        f"[data-test-experience-level-filter='{exp_key}']",
                    ]

                    exp_set = False
                    for selector in exp_selectors:
                        if await safe_click(self.page, selector):
                            logger.info(f"Experience level set: {exp_text}")
                            exp_set = True
                            break

                    if not exp_set:
                        logger.warning(f"Element not found for experience level: {exp_text}")

                    pause()

        except Exception as e:
            logger.error(f"Error setting experience level filter: {e}")

    async def _set_job_type_filter(self):
        """Set job type filter (async)"""
        if not self.job_types:
            return

        try:
            job_type_mapping = {
                "full_time": "Full-time",
                "contract": "Contract",
                "part_time": "Part-time",
                "temporary": "Temporary",
                "volunteer": "Volunteer",
                "internship": "Internship",
                "other": "Other",
            }

            for job_type_key, is_enabled in self.job_types.items():
                if is_enabled and job_type_key in job_type_mapping:
                    job_type_text = job_type_mapping[job_type_key]
                    # There are two internship checkboxes, so we need to select the second one
                    element_number = 1 if job_type_key == "internship" else 0

                    # Try multiple selector approaches
                    job_type_selectors = [
                        f"//label[contains(., '{job_type_text}')]",
                        f"//input[@value='{job_type_text}']/..",
                        f"label:has-text('{job_type_text}')",
                        f"[data-test-job-type-filter='{job_type_key}']",
                    ]

                    job_type_set = False
                    for selector in job_type_selectors:
                        if await safe_click(self.page, selector, element_number=element_number):
                            logger.info(f"Job type set: {job_type_text}")
                            job_type_set = True
                            break

                    if not job_type_set:
                        logger.warning(f"Element not found for job type: {job_type_text}")

                    pause()

        except Exception as e:
            logger.error(f"Error setting job type filter: {e}")

    async def _set_work_location_filter(self):
        """Set work location filter (remote/hybrid/on-site) - async"""
        try:
            work_location_filters = []
            if self.remote:
                work_location_filters.append("Remote")
            if self.hybrid:
                work_location_filters.append("Hybrid")
            if self.onsite:
                work_location_filters.append("On-site")

            for location_type in work_location_filters:
                # Try multiple selector approaches
                location_selectors = [
                    f"//label[contains(., '{location_type}')]",
                    f"//input[@value='{location_type}']/..",
                    f"label:has-text('{location_type}')",
                    f"[data-test-work-location-filter='{location_type.lower()}']",
                ]

                location_set = False
                for selector in location_selectors:
                    if await safe_click(self.page, selector):
                        logger.info(f"Location type set: {location_type}")
                        location_set = True
                        break

                if not location_set:
                    logger.warning(f"Element not found for location type: {location_type}")

                pause()

        except Exception as e:
            logger.error(f"Error setting work location filter: {e}")

    async def _apply_filters(self):
        """Apply set filters (async)"""
        try:
            # Find and click the "Show results" or "Apply" button
            apply_selectors = [
                "//button[contains(., 'Show') or contains(., 'Apply') or contains(., 'Done')]",
                "button[aria-label*='Show results']",
                "button[aria-label*='Apply filters']",
                ".jobs-search-dropdown__apply-button",
                ".search-reusables__filter-pill-button",
            ]

            for selector in apply_selectors:
                if await safe_click(self.page, selector, timeout=10000):
                    pause()
                    logger.info("Filters applied")
                    return True

            logger.warning("Could not find or click filter apply button")
            return False

        except Exception as e:
            logger.error(f"Error applying filters: {e}")
        return False

    async def set_search_params(self):
        """Set search parameters on LinkedIn (async)"""
        logger.info("Starting LinkedIn search parameters setup")

        try:
            # Navigate to LinkedIn jobs search
            await self.page.goto("https://www.linkedin.com/jobs/search/")
            pause(2, 3)

            # Set basic search terms (keywords and location)
            await self._set_basic_search_terms()
            pause()

            # Open advanced filters modal
            if await self._open_all_filters():
                # Set various filters
                await self._set_date_posted_filter()
                await self._set_experience_level_filter()
                await self._set_job_type_filter()
                await self._set_work_location_filter()
                await self._set_easy_apply_filter()

                # Apply all filters
                if not await self._apply_filters():
                    logger.warning("Failed to apply filters, continuing with basic search")
            else:
                logger.warning("Could not open advanced filters, using basic search only")

            logger.info("Search parameters successfully set")

        except Exception as e:
            logger.error(f"Error setting search parameters: {e}")
            raise

    def is_job_blacklisted(self, job_title: str, company_name: str, job_location: str) -> bool:
        """Check if job is blacklisted"""
        try:
            # Check company blacklist
            if company_name.lower() in [company.lower() for company in self.company_blacklist]:
                logger.info(f"Company {company_name} is blacklisted")
                return True

            # Check title blacklist
            job_title_lower = job_title.lower()
            for blacklisted_word in self.title_blacklist:
                if blacklisted_word.lower() in job_title_lower:
                    logger.info(f"Job title contains blacklisted word: {blacklisted_word}")
                    return True

            # Check location blacklist
            job_location_lower = job_location.lower()
            for blacklisted_location in self.location_blacklist:
                if blacklisted_location.lower() in job_location_lower:
                    logger.info(f"Job location is blacklisted: {blacklisted_location}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking blacklist: {e}")
            return False

    async def _set_easy_apply_filter(self):
        """Set Easy Apply filter toggle (async)"""
        if not EASY_APPLY_ONLY_MODE:
            return

        try:
            # First check if Easy Apply is already enabled
            input_selectors = [
                "//h3[contains(., 'Easy Apply')]/following::input[@role='switch'][1]",
                "input[role='switch'][data-artdeco-toggle-button='true']",
            ]

            for input_selector in input_selectors:
                input_element = await find_element_safely(self.page, input_selector)
                if input_element:
                    aria_checked = await input_element.get_attribute("aria-checked")
                    if aria_checked == "true":
                        logger.info("Easy Apply filter is already enabled")
                        return
                    break

            # Easy Apply is a toggle switch - click on the label or parent div, not the input
            easy_apply_selectors = [
                # Click on the parent div toggle container
                "//h3[contains(., 'Easy Apply')]/following::div[contains(@class, 'artdeco-toggle')][1]",
                # Alternative: find label by text
                "label[data-artdeco-toggle-label='true']:has(span:text('Toggle Easy Apply filter'))",
                # Fallback: click on the toggle text span
                "//h3[contains(., 'Easy Apply')]/following::span[@data-artdeco-toggle-text='true'][1]",
            ]

            easy_apply_toggled = False
            for selector in easy_apply_selectors:
                if await safe_click(self.page, selector):
                    logger.info("Easy Apply filter enabled")
                    easy_apply_toggled = True
                    pause()
                    break

            if not easy_apply_toggled:
                logger.warning("Could not find or toggle Easy Apply filter")

        except Exception as e:
            logger.error(f"Error setting Easy Apply filter: {e}")


if __name__ == "__main__":
    """Simple test for SearchCustomizer functionality"""
    import asyncio

    from src.utils.browser_utils import create_playwright_browser, save_browser_session

    # Test configuration
    test_config = {
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
            "temporary": True,
            "volunteer": False,
            "internship": False,
        },
        "date": {"all_time": False, "month": False, "week": False, "24_hours": True},
        "positions": ["Software Engineer", "Python Developer"],
        "locations": ["Germany"],
        "apply_once_at_company": True,
        "company_blacklist": ["wayfair", "Crossover"],
        "title_blacklist": ["word1", "word2"],
        "location_blacklist": ["Brazil"],
    }

    async def test_search_customizer():
        """Async test function for SearchCustomizer"""
        browser = None
        context = None

        try:
            # Initialize Playwright browser (async)
            browser, context, page = await create_playwright_browser()
            page = page
            logger.info("Playwright browser initialized successfully (async)")

            # Create SearchCustomizer instance
            search_customizer = SearchCustomizer(page)

            # Test parameter setting
            search_customizer.set_advanced_search_params(test_config)
            logger.info("✓ Parameters set successfully")

            # Test blacklist functionality
            test_cases = [
                ("Software Engineer", "Wayfair", "Germany", True),  # Company blacklisted
                ("Python Developer", "Google", "Brazil", True),  # Location blacklisted
                ("word1 Developer", "Microsoft", "Germany", True),  # Title blacklisted
                ("Data Scientist", "Amazon", "Germany", False),  # Not blacklisted
            ]

            for title, company, location, expected in test_cases:
                result = search_customizer.is_job_blacklisted(title, company, location)
                status = "✓" if result == expected else "✗"
                logger.info(
                    f"{status} Blacklist test: {title} at {company} in {location} -> {result}"
                )

            logger.info("✓ All tests completed successfully")

            # Test async set_search_params
            await search_customizer.set_search_params()

            pause(1000, 1000)

        except Exception as e:
            logger.error(f"Test failed: {e}")
        finally:
            # Cleanup Playwright resources
            logger.info("Cleaning up Playwright browser resources...")
            try:
                if context:
                    # Save session state before closing (async)
                    await save_browser_session(context)

                if browser:
                    await browser.close()
                    logger.info("Playwright browser closed successfully")
            except Exception as cleanup_error:
                logger.warning(f"Error during Playwright cleanup: {cleanup_error}")

    # Run the async test
    asyncio.run(test_search_customizer())
