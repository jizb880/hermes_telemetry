"""Session lifecycle hooks: on_session_start and on_session_end."""

import time
from typing import Optional

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from ..attributes import text_attr
from ..state import SessionTraceState, state_manager


_tracer: Optional[trace.Tracer] = None
_config = None
_metrics = None


def init(tracer: trace.Tracer, config, metrics) -> None:
    """Set module-level tracer, config, and metrics references."""
    global _tracer, _config, _metrics
    _tracer = tracer
    _config = config
    _metrics = metrics


def on_session_start_handler(session_id: str = "", model: str = "", platform: str = "", **kwargs):
    """Create the root session span when a new session starts."""
    try:
        if not _tracer or not _config or not _config.capture_session:
            return

        # Create root span for this session
        root_span = _tracer.start_span(
            name="hermes.session",
            kind=trace.SpanKind.SERVER,
            attributes={
                "hermes.session.id": session_id,
                "hermes.agent.model": model,
                "hermes.agent.platform": platform,
            },
        )

        # Create context with root span active
        root_context = trace.set_span_in_context(root_span)

        state = SessionTraceState(
            session_id=session_id,
            root_span=root_span,
            root_context=root_context,
            start_time=time.time(),
        )
        state_manager.set_session(session_id, state)

        if _metrics:
            _metrics.session_count.add(1, {"model": model, "platform": platform})

        print(f"[hermes_telemetry] Session started: {session_id} (model={model}, platform={platform})")

    except Exception as e:
        print(f"[hermes_telemetry] Error in on_session_start: {e}")


def on_session_end_handler(
    session_id: str = "",
    completed: bool = True,
    interrupted: bool = False,
    model: str = "",
    platform: str = "",
    **kwargs,
):
    """End the root session span and clean up state."""
    try:
        if not _config or not _config.capture_session:
            return

        state = state_manager.remove_session(session_id)
        if not state:
            return

        root_span = state.root_span
        duration_ms = (time.time() - state.start_time) * 1000

        # End any orphaned LLM span
        if state.llm_span and state.llm_span.is_recording():
            state.llm_span.set_status(StatusCode.ERROR, "Session ended before LLM call completed")
            state.llm_span.end()

        # Set final session attributes
        root_span.set_attribute("hermes.session.completed", completed)
        root_span.set_attribute("hermes.session.interrupted", interrupted)
        root_span.set_attribute("hermes.session.duration_ms", duration_ms)
        root_span.set_attribute("hermes.session.turn_count", state.turn_count)

        if interrupted:
            root_span.set_status(StatusCode.ERROR, "Session interrupted")
        else:
            root_span.set_status(StatusCode.OK)

        root_span.end()

        if _metrics:
            _metrics.session_duration.record(
                duration_ms,
                {"completed": str(completed), "interrupted": str(interrupted)},
            )

        print(
            f"[hermes_telemetry] Session ended: {session_id} "
            f"(duration={duration_ms:.0f}ms, turns={state.turn_count}, "
            f"completed={completed}, interrupted={interrupted})"
        )

    except Exception as e:
        print(f"[hermes_telemetry] Error in on_session_end: {e}")
