"""NDJSON file span exporter for OpenTelemetry."""

import json
import os
import threading
from pathlib import Path
from typing import Sequence

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode


class JsonlFileSpanExporter(SpanExporter):
    """Exports spans as newline-delimited JSON (NDJSON) to a local file.

    Each span is serialized as a single JSON line, enabling easy
    grep/jq analysis and offline debugging.
    """

    def __init__(self, file_path: str):
        self._file_path = file_path
        self._lock = threading.Lock()
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Create parent directories if they don't exist."""
        parent = Path(self._file_path).parent
        parent.mkdir(parents=True, exist_ok=True)

    def _span_to_dict(self, span: ReadableSpan) -> dict:
        """Convert a ReadableSpan to a serializable dictionary."""
        ctx = span.get_span_context()

        result = {
            "name": span.name,
            "kind": span.kind.name if span.kind else "INTERNAL",
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
            "parent_span_id": (
                format(span.parent.span_id, "016x") if span.parent else None
            ),
            "start_time_unix_nano": span.start_time,
            "end_time_unix_nano": span.end_time,
            "attributes": dict(span.attributes) if span.attributes else {},
            "status": {
                "status_code": span.status.status_code.name,
                "description": span.status.description,
            },
            "events": [
                {
                    "name": event.name,
                    "timestamp": event.timestamp,
                    "attributes": dict(event.attributes) if event.attributes else {},
                }
                for event in span.events
            ],
            "resource": {
                "attributes": dict(span.resource.attributes)
                if span.resource
                else {}
            },
            "instrumentation_scope": {
                "name": span.instrumentation_scope.name
                if span.instrumentation_scope
                else "hermes_telemetry",
            },
        }
        return result

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans by appending them as JSON lines to the file."""
        try:
            with self._lock:
                with open(self._file_path, "a", encoding="utf-8") as f:
                    for span in spans:
                        line = json.dumps(
                            self._span_to_dict(span), ensure_ascii=False, default=str
                        )
                        f.write(line + "\n")
            return SpanExportResult.SUCCESS
        except Exception as e:
            print(f"[hermes_telemetry] NDJSON export error: {e}")
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        """No-op: file handles are opened/closed per export batch."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """No-op: writes are flushed on each export call."""
        return True
