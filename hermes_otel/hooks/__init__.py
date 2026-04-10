"""Hook registration orchestrator."""

from ..config import ObservabilityConfig
from ..metrics import TelemetryMetrics
from . import llm, session, tool


def register_all_hooks(ctx, tracer, config: ObservabilityConfig, metrics: TelemetryMetrics) -> None:
    """Register all telemetry hooks with the Hermes plugin context.

    Registration order matters: session -> llm -> tool
    so that parent spans exist before child spans are created.
    """
    # Initialize all hook modules with shared tracer, config, and metrics
    session.init(tracer, config, metrics)
    llm.init(tracer, config, metrics)
    tool.init(tracer, config, metrics)

    # Register hooks in parent-first order
    if config.capture_session:
        ctx.register_hook("on_session_start", session.on_session_start_handler)
        ctx.register_hook("on_session_end", session.on_session_end_handler)

    if config.capture_llm:
        ctx.register_hook("pre_llm_call", llm.pre_llm_call_handler)
        ctx.register_hook("post_llm_call", llm.post_llm_call_handler)

    if config.capture_tool:
        ctx.register_hook("pre_tool_call", tool.pre_tool_call_handler)
        ctx.register_hook("post_tool_call", tool.post_tool_call_handler)

    registered = []
    if config.capture_session:
        registered.append("session")
    if config.capture_llm:
        registered.append("llm")
    if config.capture_tool:
        registered.append("tool")

    print(f"[hermes_telemetry] Hooks registered: {', '.join(registered)}")
