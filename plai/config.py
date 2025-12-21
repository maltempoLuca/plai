"""Shared configuration and data model placeholders for analysis pipeline."""

# TODO: Introduce data classes for VideoSpec, PoseConfig, and AnalysisResult
# in upcoming Phase 0 steps. For now, this module documents intended roles.

class _ConfigPlaceholder:
    """Temporary placeholder to signal upcoming config definitions."""

    def __repr__(self) -> str:  # pragma: no cover - trivial placeholder
        return "<ConfigPlaceholder (to be implemented)>"


CONFIG = _ConfigPlaceholder()
