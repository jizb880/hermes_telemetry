"""GlobalTracer singleton wrapping OpenTelemetry TracerProvider lifecycle."""

import atexit
import threading
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.semconv.resource import ResourceAttributes

from .config import ObservabilityConfig, resolve_ndjson_export_path
from .exporters.jsonl_file_exporter import JsonlFileSpanExporter


class GlobalTracer:
    """Singleton managing the OpenTelemetry tracer and provider lifecycle."""

    def __init__(self):
        self._lock = threading.Lock()
        self._provider: Optional[TracerProvider] = None
        self._tracer: Optional[trace.Tracer] = None
        self._initialized = False

    def init(self, config: ObservabilityConfig) -> None:
        """Initialize the tracer provider with exporters based on config."""
        with self._lock:
            if self._initialized:
                return

            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: config.service_name,
                "hermes.telemetry.version": "0.1.0",
            })

            self._provider = TracerProvider(resource=resource)

            # Console exporter for direct output
            if config.console_export_enabled:
                self._provider.add_span_processor(
                    SimpleSpanProcessor(ConsoleSpanExporter())
                )

            # NDJSON file exporter
            if config.ndjson_export_enabled:
                file_path = resolve_ndjson_export_path(config)
                self._provider.add_span_processor(
                    BatchSpanProcessor(JsonlFileSpanExporter(file_path))
                )

            trace.set_tracer_provider(self._provider)
            self._tracer = trace.get_tracer(
                "hermes_telemetry",
                "0.1.0",
            )
            self._initialized = True

            # Register atexit for graceful shutdown
            atexit.register(self.shutdown)

            print(f"[hermes_telemetry] Initialized (service={config.service_name})")
            if config.console_export_enabled:
                print("[hermes_telemetry] Console export: enabled")
            if config.ndjson_export_enabled:
                print(f"[hermes_telemetry] NDJSON export: {resolve_ndjson_export_path(config)}")

    def get_tracer(self) -> trace.Tracer:
        """Return the OTel Tracer instance."""
        if self._tracer is None:
            raise RuntimeError("GlobalTracer not initialized. Call init() first.")
        return self._tracer

    def shutdown(self) -> None:
        """Flush pending spans and shut down the provider."""
        with self._lock:
            if self._provider and self._initialized:
                try:
                    self._provider.force_flush()
                    self._provider.shutdown()
                except Exception:
                    pass
                self._initialized = False


# Global singleton
global_tracer = GlobalTracer()
