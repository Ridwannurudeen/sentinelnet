"""Structured JSON logging for SentinelNet.

Format: one JSON object per line with `time`, `level`, `logger`, `message`,
plus any extra fields passed via `logger.info("msg", extra={...})`.

Toggle with the env var `LOG_FORMAT`: "json" (default in prod) or "text"
(default if stdout is a TTY — friendlier for local dev).
"""
from __future__ import annotations

import datetime as _dt
import logging
import os
import sys

from pythonjsonlogger import jsonlogger


_RESERVED = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "asctime", "taskName",
}


class SentinelJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["time"] = _dt.datetime.fromtimestamp(
            record.created, tz=_dt.timezone.utc
        ).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        for k, v in record.__dict__.items():
            if k not in _RESERVED and not k.startswith("_") and k not in log_record:
                try:
                    log_record[k] = v
                except Exception:
                    pass


def configure(level: str = "INFO") -> None:
    """Configure the root logger plus uvicorn's loggers.

    Idempotent — safe to call multiple times.
    """
    fmt_choice = os.environ.get("LOG_FORMAT", "").lower()
    if not fmt_choice:
        fmt_choice = "text" if sys.stdout.isatty() else "json"

    handler = logging.StreamHandler(sys.stdout)
    if fmt_choice == "json":
        handler.setFormatter(
            SentinelJsonFormatter("%(time)s %(level)s %(logger)s %(message)s")
        )
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.addHandler(handler)
        lg.propagate = False
        lg.setLevel(level.upper())
