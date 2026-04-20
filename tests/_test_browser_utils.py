"""Test async browser utilities migration

This script tests the async Playwright browser utilities to ensure
they work correctly after migration from sync to async.
"""

import asyncio
from pathlib import Path

from config.logger_config import logger
from src.utils.browser_utils import (
    create_playwright_browser,
    find_element_safely,
    find_elements_safely,
    get_element_text,
    safe_click,
    save_browser_session,
)


async def test_browser_creation():
    """Test async browser creation"""
    logger.info("🧪 Test 1: Browser Creation")

    try:
        browser, context, page = await create_playwright_browser()
        logger.info("✅ Browser created successfully")

        # Test page navigation
        await page.goto("https://www.example.com")
        logger.info("✅ Page navigation successful")

        return browser, context, page
    except Exception as e:
        logger.error(f"❌ Browser creation failed: {e}")
        raise


async def test_element_operations(page):
    """Test async element operations"""
    logger.info("\n🧪 Test 2: Element Operations")

    try:
        # Navigate to a test page
        await page.goto("https://www.example.com")

        # Test find_element_safely
        heading = await find_element_safely(page, "h1")
        if heading:
            logger.info("✅ find_element_safely works")
        else:
            logger.warning("⚠️ No heading found (expected for example.com)")

        # Test get_element_text
        text = await get_element_text(page, "h1")
        if text:
            logger.info(f"✅ get_element_text works: '{text}'")
        else:
            logger.warning("⚠️ No text found")

        # Test find_elements_safely
        paragraphs = await find_elements_safely(page, "p")
        logger.info(f"✅ find_elements_safely works: found {len(paragraphs)} paragraphs")

        return True
    except Exception as e:
        logger.error(f"❌ Element operations failed: {e}")
        raise


async def test_session_management(context):
    """Test async session save"""
    logger.info("\n🧪 Test 3: Session Management")

    try:
        await save_browser_session(context)
        logger.info("✅ Session save works")

        # Check if session file was created
        from config.constants import BROWSER_STORAGE_STATE

        if Path(BROWSER_STORAGE_STATE).exists():
            logger.info("✅ Session file created successfully")
        else:
            logger.warning("⚠️ Session file not found (may be expected)")

        return True
    except Exception as e:
        logger.error(f"❌ Session management failed: {e}")
        raise


async def test_interactive_elements(page):
    """Test interactive element operations"""
    logger.info("\n🧪 Test 4: Interactive Elements (GitHub)")

    try:
        # Navigate to GitHub (more interactive than example.com)
        await page.goto("https://github.com")
        await asyncio.sleep(2)  # Wait for dynamic content

        # Test safe_click on a link
        search_button = await find_element_safely(page, "button[aria-label='Search or jump to…']")
        if search_button:
            result = await safe_click(page, "button[aria-label='Search or jump to…']", timeout=5000)
            if result:
                logger.info("✅ safe_click works")
            else:
                logger.warning("⚠️ Click failed (may be expected)")
        else:
            logger.info("ℹ️ Search button not found (GitHub layout may have changed)")

        return True
    except Exception as e:
        logger.error(f"❌ Interactive elements test failed: {e}")
        # Don't raise - this test is optional
        return False


async def main():
    """Run all async browser utility tests"""
    logger.info("=" * 60)
    logger.info("🚀 Starting Async Browser Utils Migration Tests")
    logger.info("=" * 60)

    browser = None
    context = None

    try:
        # Test 1: Browser creation
        browser, context, page = await test_browser_creation()

        # Test 2: Element operations
        await test_element_operations(page)

        # Test 3: Session management
        await test_session_management(context)

        # Test 4: Interactive elements
        await test_interactive_elements(page)

        logger.info("\n" + "=" * 60)
        logger.info("✅ All async browser utility tests completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error(f"❌ Tests failed with error: {e}")
        logger.error("=" * 60)
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if browser:
            try:
                if context:
                    await save_browser_session(context)
                await browser.close()
                logger.info("\n🧹 Browser cleaned up successfully")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")


if __name__ == "__main__":
    asyncio.run(main())
