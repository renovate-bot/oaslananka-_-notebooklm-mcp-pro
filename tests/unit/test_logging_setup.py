import structlog
from _pytest.capture import CaptureFixture

from nlm_mcp.config import LogFormat, Settings
from nlm_mcp.logging_setup import configure_logging, get_logger


def test_configure_logging_emits_json(capsys: CaptureFixture[str]) -> None:
    configure_logging(Settings(log_format=LogFormat.JSON))

    get_logger("nlm_mcp.tests").info("core_started", component="logging")
    captured = capsys.readouterr()

    assert '"event": "core_started"' in captured.err
    assert '"component": "logging"' in captured.err


def test_get_logger_returns_structlog_bound_logger() -> None:
    logger = get_logger("nlm_mcp.tests")

    assert isinstance(logger, structlog.stdlib.BoundLogger)
