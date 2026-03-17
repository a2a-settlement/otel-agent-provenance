"""OpenTelemetry semantic conventions and instrumentation for agent provenance.

Provides:
- ``conventions``: Attribute key constants for provenance, derivation, acceptance, federation
- ``spans``: Span builder helpers for instrumenting agent provenance
- ``federation``: Federation span builders (peering, VC import, Trust Discount, health)
- ``adapters``: Framework-specific adapters (Google, Azure, AutoGen)
- ``instruments``: A2A-SE exchange/mediator/shim instrumentation
"""

from otel_agent_provenance.conventions import (
    AcceptanceAttributes,
    DerivationAttributes,
    FederationAttributes,
    ProvenanceAttributes,
)
from otel_agent_provenance.federation import FederationSpan
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
    "FederationAttributes",
    "FederationSpan",
    "ProvenanceAttributes",
    "ProvenanceSpan",
]
