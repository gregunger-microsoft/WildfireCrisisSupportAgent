"""Structured JSON logging + optional OpenTelemetry/Azure Monitor."""
from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def setup_observability() -> None:
    """Configure structured logging and optional OTel tracing."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
    ))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    # Optional Application Insights via OpenTelemetry
    conn_str = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    if conn_str:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor
            configure_azure_monitor(connection_string=conn_str)
            logging.getLogger(__name__).info("Azure Monitor OpenTelemetry configured")
        except ImportError:
            logging.getLogger(__name__).warning(
                "azure-monitor-opentelemetry not installed; skipping App Insights"
            )
