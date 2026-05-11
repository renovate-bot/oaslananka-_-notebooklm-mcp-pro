from collections.abc import Awaitable, Callable
from typing import TypeVar

from notebooklm import AuthError, RateLimitError
from tenacity import wait_none

from nlm_mcp.backend.retry import is_retryable_exception, run_with_retry

T = TypeVar("T")


async def _no_sleep(_delay: float) -> None:
    return None


def _operation(values: list[object]) -> Callable[[], Awaitable[str]]:
    async def run() -> str:
        value = values.pop(0)
        if isinstance(value, Exception):
            raise value
        return str(value)

    return run


async def test_run_with_retry_returns_after_transient_failure() -> None:
    values: list[object] = [RateLimitError("limited"), "ok"]

    result = await run_with_retry(
        _operation(values),
        operation_name="unit.retry",
        wait_strategy=wait_none(),
        sleep=_no_sleep,
    )

    assert result == "ok"
    assert values == []


async def test_run_with_retry_stops_after_max_attempts() -> None:
    values: list[object] = [RateLimitError("limited"), RateLimitError("limited")]

    try:
        await run_with_retry(
            _operation(values),
            operation_name="unit.retry",
            max_attempts=2,
            wait_strategy=wait_none(),
            sleep=_no_sleep,
        )
    except RateLimitError:
        assert values == []
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("retry operation unexpectedly succeeded")


async def test_run_with_retry_does_not_retry_auth_errors() -> None:
    values: list[object] = [AuthError("expired"), "ok"]

    try:
        await run_with_retry(
            _operation(values),
            operation_name="unit.retry",
            wait_strategy=wait_none(),
            sleep=_no_sleep,
        )
    except AuthError:
        assert values == ["ok"]
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("non-retryable operation unexpectedly succeeded")


def test_builtin_timeout_is_retryable() -> None:
    assert is_retryable_exception(TimeoutError("temporary")) is True
