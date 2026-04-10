"""Tool call hooks: pre_tool_call and post_tool_call."""

import time
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import StatusCode

from ..attributes import json_attr
from ..state import PendingToolSpan, state_manager


_tracer: Optional[trace.Tracer] = None
_config = None
_metrics = None


def init(tracer: trace.Tracer, config, metrics) -> None:
    """Set module-level tracer, config, and metrics references."""
    global _tracer, _config, _metrics
    _tracer = tracer
    _config = config
    _metrics = metrics


def _resolve_session_id(**kwargs) -> str:
    """Resolve session_id from kwargs (tool hooks may pass task_id or session_id)."""
    return kwargs.get("session_id", "") or kwargs.get("task_id", "")


def pre_tool_call_handler(
    tool_name: str = "",
    args: dict = None,
    task_id: str = "",
    **kwargs,
):
    """Create a tool span and push it onto the tool stack."""
    try:
        if not _tracer or not _config or not _config.capture_tool:
            return

        session_id = _resolve_session_id(task_id=task_id, **kwargs)
        state = state_manager.get_session(session_id)

        # Determine parent context: prefer LLM span, fall back to session root
        parent_ctx = None
        if state:
            parent_ctx = state.llm_context or state.root_context

        span_name = f"hermes.tool.{tool_name}"
        tool_span = _tracer.start_span(
            name=span_name,
            kind=trace.SpanKind.INTERNAL,
            context=parent_ctx,
            attributes={
                "hermes.tool.name": tool_name,
                "hermes.tool.task_id": task_id,
                "hermes.session.id": session_id,
            },
        )

        if _config.capture_tool_input and args:
            tool_span.set_attribute("hermes.tool.input", json_attr(args))

        # Push onto tool stack (keyed by task_id for subagent isolation)
        stack_key = task_id or session_id
        pending = PendingToolSpan(
            span=tool_span,
            tool_name=tool_name,
            start_time=time.time(),
        )
        state_manager.push_tool(stack_key, pending)

        if _metrics:
            _metrics.tool_call_count.add(1, {"tool_name": tool_name})

        print(f"[hermes_telemetry] Tool call started: {tool_name} (task={task_id})")

    except Exception as e:
        print(f"[hermes_telemetry] Error in pre_tool_call: {e}")


def post_tool_call_handler(
    tool_name: str = "",
    args: dict = None,
    result: str = "",
    task_id: str = "",
    **kwargs,
):
    """Pop the tool span from the stack and end it."""
    try:
        if not _config or not _config.capture_tool:
            return

        stack_key = task_id or _resolve_session_id(task_id=task_id, **kwargs)
        pending = state_manager.pop_tool(stack_key)

        if not pending:
            print(f"[hermes_telemetry] Warning: no pending tool span for {tool_name} (task={task_id})")
            return

        tool_span = pending.span
        duration_ms = (time.time() - pending.start_time) * 1000

        if _config.capture_tool_output and result:
            tool_span.set_attribute("hermes.tool.output", json_attr(result))

        tool_span.set_attribute("hermes.tool.duration_ms", duration_ms)

        # Check for errors in result
        is_error = False
        if isinstance(result, str) and '"error"' in result.lower():
            is_error = True
            tool_span.set_status(StatusCode.ERROR, f"Tool {tool_name} returned error")
            if _metrics:
                _metrics.tool_error_count.add(1, {"tool_name": tool_name})
        else:
            tool_span.set_status(StatusCode.OK)

        tool_span.end()

        if _metrics:
            _metrics.tool_call_duration.record(duration_ms, {"tool_name": tool_name})

        print(
            f"[hermes_telemetry] Tool call ended: {tool_name} "
            f"(duration={duration_ms:.0f}ms, error={is_error})"
        )

    except Exception as e:
        print(f"[hermes_telemetry] Error in post_tool_call: {e}")
