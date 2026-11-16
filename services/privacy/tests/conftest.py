"""Shared fixtures. All partner ids are synthetic vignette ids (V1A/V1B, V4A/V4B) - P-11."""
from __future__ import annotations

import pytest

from privacy.apsi import ApsiService
from privacy.audit import AuditLog
from privacy.authority import Authority
from privacy.consent import ConsentService


@pytest.fixture(scope="session")
def authority():
    return Authority()  # one 2048-bit keygen per test session keeps runtime low


@pytest.fixture
def audit():
    return AuditLog()


@pytest.fixture
def consents(audit):
    return ConsentService(audit=audit)


@pytest.fixture
def service(authority, consents, audit):
    return ApsiService(authority=authority.public_key, consents=consents, audit=audit)


@pytest.fixture
def couple(consents):
    """Two mutually-referencing active consents for synthetic partners V4A / V4B."""
    return consents.create("V4A", "V4B"), consents.create("V4B", "V4A")
