"""privacy - Authorized PSI, consent, audit, cascade token, small-cell suppression.

Requirements: R-PRIV-1 (APSI), R-PRIV-2 (Consent + revocation purge), R-PRIV-4 (cascade token).
Public entry point for the API: ``privacy.apsi.run(consent_a, consent_b, signed_a, signed_b)``.
"""
from . import apsi, audit, authority, cascade, consent, suppress  # noqa: F401
