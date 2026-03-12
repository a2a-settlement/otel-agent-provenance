"""OpenTelemetry semantic conventions and instrumentation for agent provenance.

Provides:
- ``conventions``: Attribute key constants for provenance, derivation, and acceptance
- ``spans``: Span builder helpers for instrumenting agent provenance
- ``adapters``: Framework-specific adapters (Google, Azure, AutoGen)
- ``instruments``: A2A-SE exchange/mediator/shim instrumentation
"""

from otel_agent_provenance.conventions import (
    AcceptanceAttributes,
    DerivationAttributes,
    ProvenanceAttributes,
)
from otel_agent_provenance.spans import (
    AcceptanceSpan,
    DerivationSpan,
    ProvenanceSpan,
)

__version__ = "0.1.0"

__all__ = [
    "AcceptanceAttributes",
    "AcceptanceSpan",
    "DerivationAttributes",
    "DerivationSpan",
    "ProvenanceAttributes",
    "ProvenanceSpan",
]
