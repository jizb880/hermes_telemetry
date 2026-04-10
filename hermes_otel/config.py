"""Configuration loading and parsing for hermes_telemetry."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ObservabilityConfig:
    """Telemetry configuration for Hermes Agent observability."""

    enabled: bool = True
    service_name: str = "hermes-agent"

    # Console output
    console_export_enabled: bool = True

    # NDJSON file export
    ndjson_export_enabled: bool = True
    ndjson_export_path: str = "."

    # Hook capture toggles
    capture_session: bool = True
    capture_llm: bool = True
    capture_tool: bool = True

    # Granular input/output capture
    capture_llm_input: bool = True
    capture_llm_output: bool = True
    capture_tool_input: bool = True
    capture_tool_output: bool = True


def parse_config(raw: dict) -> ObservabilityConfig:
    """Parse a raw dictionary into an ObservabilityConfig, using defaults for missing keys."""
    cfg = ObservabilityConfig()
    for key in ObservabilityConfig.__dataclass_fields__:
        if key in raw:
            setattr(cfg, key, raw[key])
    return cfg


def load_config(explicit_path: Optional[str] = None) -> ObservabilityConfig:
    """Load configuration from JSON file with fallback chain.

    Resolution order:
    1. explicit_path parameter
    2. HERMES_TELEMETRY_CONFIG environment variable
    3. Plugin directory's config/observability.json
    4. Built-in defaults
    """
    candidates = []

    if explicit_path:
        candidates.append(explicit_path)

    env_path = os.environ.get("HERMES_TELEMETRY_CONFIG")
    if env_path:
        candidates.append(env_path)

    # Plugin directory default
    plugin_dir = Path(__file__).resolve().parent.parent
    candidates.append(str(plugin_dir / "config" / "observability.json"))

    # ~/.hermes/plugins path
    home_plugin = Path.home() / ".hermes" / "plugins" / "hermes_telemetry" / "config" / "observability.json"
    candidates.append(str(home_plugin))

    for path in candidates:
        p = Path(path)
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                return parse_config(raw)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[hermes_telemetry] Warning: failed to load config from {p}: {e}")

    return ObservabilityConfig()


def resolve_ndjson_export_path(cfg: ObservabilityConfig) -> str:
    """Resolve the NDJSON export file path from config."""
    path = cfg.ndjson_export_path
    if path.endswith(".jsonl") or path.endswith(".ndjson"):
        return path
    return str(Path(path) / "hermes-otel-spans.jsonl")
