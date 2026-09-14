"""
Retry utilities with exponential backoff for LLM and MCP calls.
"""

import asyncio
import functools
import logging
import time

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_BACKOFF_FACTOR = 2.0

# Exceptions worth retrying (network, timeout, rate limit)
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    OSError,
)


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
):
    """
    Decorator that retries a synchronous function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for delay after each retry.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt == max_retries:
                        logger.error(
                            "[retry] %s failed after %d attempts: %s",
                            func.__name__,
                            max_retries + 1,
                            exc,
                        )
                        raise

                    delay = base_delay * (backoff_factor ** attempt)
                    logger.warning(
                        "[retry] %s attempt %d/%d failed (%s), retrying in %.1fs...",
                        func.__name__,
                        attempt + 1,
                        max_retries + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)

            raise last_exception
        return wrapper
    return decorator


def with_async_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
):
    """
    Decorator that retries an async function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        backoff_factor: Multiplier for delay after each retry.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    if attempt == max_retries:
                        logger.error(
                            "[retry] %s failed after %d attempts: %s",
                            func.__name__,
                            max_retries + 1,
                            exc,
                        )
                        raise

                    delay = base_delay * (backoff_factor ** attempt)
                    logger.warning(
                        "[retry] %s attempt %d/%d failed (%s), retrying in %.1fs...",
                        func.__name__,
                        attempt + 1,
                        max_retries + 1,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)

            raise last_exception
        return wrapper
    return decorator
