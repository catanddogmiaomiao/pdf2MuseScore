"""Local, conservative MusicXML review. No OMR or GUI dependencies."""
from .engine import ValidationConfig, validate_score, read_score

__all__ = ["ValidationConfig", "validate_score", "read_score"]
