import asyncio
import ctypes
import os
import signal
import time
from threading import Event
from typing import Any

from config.logger_config import logger

_shutdown_handlers_registered = False
_windows_console_handler = None


class BrowserClosedError(RuntimeError):
    """Raised when the browser window is closed during a run."""


class GracefulShutdownRequested(RuntimeError):
    """Raised when the application should stop after cleanup."""


class RuntimeController:
    """Coordinates shutdown and browser-close reactions across sync/async boundaries."""

    def __init__(self) -> None:
        self.shutdown_requested = Event()
        self.cleanup_complete = Event()
        self.cleanup_complete.set()

    def request_shutdown(self, source: str) -> None:
        if not self.shutdown_requested.is_set():
            logger.warning(f"Shutdown requested via {source}. Finishing current cleanup.")
        self.shutdown_requested.set()

    def is_shutdown_requested(self) -> bool:
        return self.shutdown_requested.is_set()

    def begin_run(self) -> None:
        self.cleanup_complete.clear()

    def finish_run(self) -> None:
        self.cleanup_complete.set()

    def wait_for_cleanup(self, timeout: float = 15.0) -> bool:
        return self.cleanup_complete.wait(timeout)


runtime_controller = RuntimeController()


def _handle_shutdown_signal(signum, _frame) -> None:
    """Convert OS signals into a graceful shutdown request."""
    try:
        signal_name = signal.Signals(signum).name
    except ValueError:
        signal_name = str(signum)
    runtime_controller.request_shutdown(f"signal {signal_name}")


def register_shutdown_handlers() -> None:
    """Register SIGINT/SIGTERM and Windows console-close handlers once."""
    global _shutdown_handlers_registered, _windows_console_handler
    if _shutdown_handlers_registered:
        return

    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_shutdown_signal)

    if os.name == "nt":
        handler_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
        event_names = {
            0: "CTRL_C_EVENT",
            1: "CTRL_BREAK_EVENT",
            2: "CTRL_CLOSE_EVENT",
            5: "CTRL_LOGOFF_EVENT",
            6: "CTRL_SHUTDOWN_EVENT",
        }

        def console_handler(ctrl_type: int) -> bool:
            runtime_controller.request_shutdown(
                f"console event {event_names.get(ctrl_type, ctrl_type)}"
            )
            runtime_controller.wait_for_cleanup(timeout=15.0)
            return True

        _windows_console_handler = handler_type(console_handler)
        ctypes.windll.kernel32.SetConsoleCtrlHandler(_windows_console_handler, True)

    _shutdown_handlers_registered = True


def attach_browser_close_watchers(browser: Any, context: Any, page: Any) -> asyncio.Event:
    """Return an event that fires when the browser/page/context is closed."""
    browser_closed = asyncio.Event()

    def mark_closed(target_name: str) -> None:
        if not browser_closed.is_set():
            logger.warning(
                f"{target_name} was closed. Press Ctrl+C to stop, or the bot will reopen the browser shortly."
            )
            browser_closed.set()

    browser.on("disconnected", lambda: mark_closed("Browser"))
    context.on("close", lambda: mark_closed("Browser context"))
    page.on("close", lambda: mark_closed("Browser page"))
    return browser_closed


async def _wait_for_shutdown_request() -> str:
    await asyncio.to_thread(runtime_controller.shutdown_requested.wait)
    return "shutdown"


async def _wait_for_browser_close(browser_closed: asyncio.Event) -> str:
    await browser_closed.wait()
    return "browser_closed"


async def _cancel_task(task: asyncio.Task | None) -> None:
    if task is None or task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def run_with_runtime_guards(bot: Any, browser_closed: asyncio.Event):
    """Race the bot against runtime control events."""
    apply_task = asyncio.create_task(bot.start_apply())
    browser_task = asyncio.create_task(_wait_for_browser_close(browser_closed))
    shutdown_task = asyncio.create_task(_wait_for_shutdown_request())

    try:
        done, _pending = await asyncio.wait(
            {apply_task, browser_task, shutdown_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if apply_task in done:
            return await apply_task

        if browser_task in done:
            await _cancel_task(apply_task)
            raise BrowserClosedError("Browser window closed by user")

        if shutdown_task in done:
            await _cancel_task(apply_task)
            raise GracefulShutdownRequested("Shutdown requested")
    finally:
        await _cancel_task(browser_task)
        await _cancel_task(shutdown_task)


async def sleep_with_shutdown(seconds: int) -> bool:
    """Sleep in short chunks so shutdown requests are honored quickly."""
    for _ in range(seconds):
        if runtime_controller.is_shutdown_requested():
            return False
        await asyncio.sleep(1)
    return not runtime_controller.is_shutdown_requested()


def countdown_before_restart(seconds: int = 5) -> bool:
    """Give the user a short window to cancel restart after browser closure."""
    logger.warning(
        "I can reopen the browser and continue. Press Ctrl+C now to stop applications."
    )
    for remaining in range(seconds, 0, -1):
        if runtime_controller.is_shutdown_requested():
            logger.info("Restart cancelled by shutdown request")
            return False
        logger.warning(f"Reopening browser in {remaining}...")
        time.sleep(1)
    return not runtime_controller.is_shutdown_requested()
