"""Hermes Telemetry Plugin - OpenTelemetry observability for Hermes Agent.

This is the plugin entry point. Hermes Agent calls register(ctx) during plugin loading.
"""

from .hermes_otel.config import load_config
from .hermes_otel.hooks import register_all_hooks
from .hermes_otel.metrics import TelemetryMetrics
from .hermes_otel.tracer import global_tracer


def register(ctx):
    """Plugin entry point called by Hermes Agent during plugin discovery.

    Args:
        ctx: Hermes PluginContext providing register_hook() and register_tool().
    """
    try:
        config = load_config()

        if not config.enabled:
            print("[hermes_telemetry] Plugin disabled via configuration.")
            return

        # Initialize OpenTelemetry tracer
        global_tracer.init(config)
        tracer = global_tracer.get_tracer()

        # Initialize metrics
        telemetry_metrics = TelemetryMetrics()

        # Register all hooks
        register_all_hooks(ctx, tracer, config, telemetry_metrics)

        print("[hermes_telemetry] Plugin registered successfully.")

    except Exception as e:
        print(f"[hermes_telemetry] Failed to register plugin: {e}")
