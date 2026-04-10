"""Session-scoped state management for trace correlation across hooks."""

import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from opentelemetry import context as otel_context
from opentelemetry import trace


@dataclass
class SessionTraceState:
    """Trace state for a single session lifecycle."""

    session_id: str
    root_span: trace.Span
    root_context: otel_context.Context
    llm_span: Optional[trace.Span] = None
    llm_context: Optional[otel_context.Context] = None
    start_time: float = 0.0
    turn_count: int = 0


@dataclass
class PendingToolSpan:
    """A tool span waiting for its post_tool_call to close it."""

    span: trace.Span
    tool_name: str
    start_time: float


class StateManager:
    """Thread-safe state manager for session traces and tool stacks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: Dict[str, SessionTraceState] = {}
        self._tool_stacks: Dict[str, List[PendingToolSpan]] = {}

    # --- Session state ---

    def set_session(self, session_id: str, state: SessionTraceState) -> None:
        with self._lock:
            self._sessions[session_id] = state

    def get_session(self, session_id: str) -> Optional[SessionTraceState]:
        with self._lock:
            return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> Optional[SessionTraceState]:
        with self._lock:
            return self._sessions.pop(session_id, None)

    # --- Tool stacks (keyed by task_id) ---

    def push_tool(self, task_id: str, pending: PendingToolSpan) -> None:
        with self._lock:
            if task_id not in self._tool_stacks:
                self._tool_stacks[task_id] = []
            self._tool_stacks[task_id].append(pending)

    def pop_tool(self, task_id: str) -> Optional[PendingToolSpan]:
        with self._lock:
            stack = self._tool_stacks.get(task_id)
            if stack:
                pending = stack.pop()
                if not stack:
                    del self._tool_stacks[task_id]
                return pending
            return None

    def clear_tool_stack(self, task_id: str) -> List[PendingToolSpan]:
        """Pop all remaining tool spans for a task (cleanup orphans)."""
        with self._lock:
            return self._tool_stacks.pop(task_id, [])


# Global singleton
state_manager = StateManager()
