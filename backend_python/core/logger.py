import logging
from pathlib import Path

try:
    import structlog
except Exception:
    structlog = None

BASE_DIR = Path(__file__).parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "nova.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

if structlog is not None:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger("nova")
else:

    class _FallbackLogger:
        def __init__(self, name: str) -> None:
            self._logger = logging.getLogger(name)

        def _format(self, event: str, fields: dict) -> str:
            if not fields:
                return str(event)
            extras = " ".join(f"{key}={value!r}" for key, value in sorted(fields.items()))
            return f"{event} | {extras}"

        def info(self, event: str, **fields) -> None:
            self._logger.info(self._format(event, fields))

        def warning(self, event: str, **fields) -> None:
            self._logger.warning(self._format(event, fields))

        def error(self, event: str, **fields) -> None:
            exc_info = fields.pop("exc_info", None)
            self._logger.error(self._format(event, fields), exc_info=exc_info)

    logger = _FallbackLogger("nova")
