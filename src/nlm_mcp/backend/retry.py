"""Retry policies for NotebookLM backend calls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import httpx
from notebooklm import NetworkError, RateLimitError, RPCTimeoutError, ServerError
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

T = TypeVar("T")
SleepCallback = Callable[[float], Awaitable[None]]


def is_retryable_exception(exc: BaseException) -> bool:
    """Return whether a backend exception should be retried."""
    return isinstance(
        exc,
        (
            RateLimitError,
            NetworkError,
            ServerError,
            RPCTimeoutError,
            TimeoutError,
            httpx.TimeoutException,
            httpx.TransportError,
        ),
    )


async def run_with_retry(
    operation: Callable[[], Awaitable[T]],
    *,
    operation_name: str,
    max_attempts: int = 5,
    wait_strategy: Any | None = None,
    sleep: SleepCallback | None = None,
) -> T:
    """Run an async backend operation with the standard retry policy."""
    _ = operation_name
    wait_config = (
        wait_strategy if wait_strategy is not None else wait_exponential(multiplier=1, max=30)
    )
    retry_config = retry_if_exception(is_retryable_exception)
    if sleep is None:
        retrying = AsyncRetrying(
            retry=retry_config,
            stop=stop_after_attempt(max_attempts),
            wait=wait_config,
            reraise=True,
        )
    else:
        retrying = AsyncRetrying(
            retry=retry_config,
            stop=stop_after_attempt(max_attempts),
            wait=wait_config,
            sleep=sleep,
            reraise=True,
        )

    async for attempt in retrying:
        with attempt:
            return await operation()

    # tenacity reraise=True guarantees the final retry exception is propagated.
    raise AssertionError(
        "unreachable: tenacity reraise=True ensures exception propagation"
    )  # pragma: no cover
