"""LLM call hooks: pre_llm_call and post_llm_call."""

import time
from typing import Optional

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.trace import StatusCode

from ..attributes import text_attr
from ..state import state_manager


_tracer: Optional[trace.Tracer] = None
_config = None
_metrics = None


def init(tracer: trace.Tracer, config, metrics) -> None:
    """Set module-level tracer, config, and metrics references."""
    global _tracer, _config, _metrics
    _tracer = tracer
    _config = config
    _metrics = metrics


def pre_llm_call_handler(
    session_id: str = "",
    user_message: str = "",
    conversation_history: list = None,
    is_first_turn: bool = False,
    model: str = "",
    platform: str = "",
    **kwargs,
):
    """Create a child span for the LLM call under the session root."""
    try:
        if not _tracer or not _config or not _config.capture_llm:
            return None

        state = state_manager.get_session(session_id)
        if not state:
            return None

        # Create LLM span as child of session root span
        parent_ctx = state.root_context
        llm_span = _tracer.start_span(
            name="hermes.llm.call",
            kind=trace.SpanKind.CLIENT,
            context=parent_ctx,
            attributes={
                "hermes.session.id": session_id,
                "hermes.llm.model": model,
                "hermes.llm.platform": platform,
                "hermes.llm.is_first_turn": is_first_turn,
                "hermes.llm.conversation_length": len(conversation_history) if conversation_history else 0,
            },
        )

        if _config.capture_llm_input and user_message:
            llm_span.set_attribute("gen_ai.prompt", text_attr(user_message))

        # Store LLM span in session state
        state.llm_span = llm_span
        state.llm_context = trace.set_span_in_context(llm_span, parent_ctx)
        state.turn_count += 1

        if _metrics:
            _metrics.llm_call_count.add(1, {"model": model, "is_first_turn": str(is_first_turn)})

        print(f"[hermes_telemetry] LLM call started: session={session_id}, turn={state.turn_count}")

        # Return None - we don't inject context into the user message
        return None

    except Exception as e:
        print(f"[hermes_telemetry] Error in pre_llm_call: {e}")
        return None


def post_llm_call_handler(
    session_id: str = "",
    user_message: str = "",
    assistant_response: str = "",
    conversation_history: list = None,
    model: str = "",
    platform: str = "",
    **kwargs,
):
    """End the LLM call span and record response metrics."""
    try:
        if not _config or not _config.capture_llm:
            return

        state = state_manager.get_session(session_id)
        if not state or not state.llm_span:
            return

        llm_span = state.llm_span

        if _config.capture_llm_output and assistant_response:
            llm_span.set_attribute("gen_ai.completion", text_attr(assistant_response))

        llm_span.set_attribute("hermes.llm.response_length", len(assistant_response) if assistant_response else 0)
        llm_span.set_status(StatusCode.OK)
        llm_span.end()

        if _metrics:
            # Approximate duration from span timestamps
            _metrics.llm_call_duration.record(
                (llm_span.end_time - llm_span.start_time) / 1e6,  # ns -> ms
                {"model": model},
            )

        # Clear LLM span from state
        state.llm_span = None
        state.llm_context = None

        print(
            f"[hermes_telemetry] LLM call ended: session={session_id}, "
            f"response_len={len(assistant_response) if assistant_response else 0}"
        )

    except Exception as e:
        print(f"[hermes_telemetry] Error in post_llm_call: {e}")
