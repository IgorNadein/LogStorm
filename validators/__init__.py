"""Compatibility exports for analyzer validators.

New code should import from ``analyzer.validators``.
"""

from analyzer.validators import AbsenceValidator, TimeValidator

__all__ = ['TimeValidator', 'AbsenceValidator']
