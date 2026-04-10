"""OpenTelemetry metrics definitions for Hermes Agent telemetry."""

from opentelemetry import metrics


class TelemetryMetrics:
    """Container for all telemetry counters and histograms."""

    def __init__(self, meter_name: str = "hermes_telemetry"):
        meter = metrics.get_meter(meter_name, "0.1.0")

        # --- Counters ---
        self.session_count = meter.create_counter(
            name="hermes.session.count",
            description="Total number of sessions started",
            unit="1",
        )

        self.llm_call_count = meter.create_counter(
            name="hermes.llm.call.count",
            description="Total number of LLM calls",
            unit="1",
        )

        self.tool_call_count = meter.create_counter(
            name="hermes.tool.call.count",
            description="Total number of tool invocations",
            unit="1",
        )

        self.tool_error_count = meter.create_counter(
            name="hermes.tool.error.count",
            description="Total number of tool errors",
            unit="1",
        )

        # --- Histograms ---
        self.session_duration = meter.create_histogram(
            name="hermes.session.duration_ms",
            description="Session duration in milliseconds",
            unit="ms",
        )

        self.llm_call_duration = meter.create_histogram(
            name="hermes.llm.call.duration_ms",
            description="LLM call duration in milliseconds",
            unit="ms",
        )

        self.tool_call_duration = meter.create_histogram(
            name="hermes.tool.call.duration_ms",
            description="Tool call duration in milliseconds",
            unit="ms",
        )
