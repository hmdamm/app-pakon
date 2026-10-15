"""Unit tests for the inventory orchestrator."""

from unittest.mock import MagicMock
from appharbor.domain.models import (
    ConfidenceLevel,
    FilterCategory,
    InstallationRecord,
    ProviderCapabilities,
    ScopeEnum,
    SourceEnum,
)
from appharbor.inventory.orchestrator import InventoryOrchestrator
from appharbor.providers.base import BaseProvider


class FakeProvider(BaseProvider):
    def __init__(self, provider_id: str, records: list[InstallationRecord], should_fail: bool = False):
        self._id = provider_id
        self._records = records
        self._should_fail = should_fail

    @property
    def provider_id(self) -> str:
        return self._id

    @property
    def display_name(self) -> str:
        return self._id.capitalize()

    def detect_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(provider_id=self._id, is_available=True)

    def scan_applications(self, progress_callback=None) -> list[InstallationRecord]:
        if self._should_fail:
            raise RuntimeError(f"Simulated crash in {self._id}")
        return self._records

    def plan_uninstall(self, record, keep_data=True):
        pass

    def execute_uninstall(self, plan, progress_callback=None):
        pass


def test_orchestrator_failure_isolation():
    # Provider 1 succeeds
    p1 = FakeProvider(
        "provider1",
        [
            InstallationRecord(
                id="p1:sys:app1",
                name="App One",
                package_id="app1",
                source=SourceEnum.FLATPAK,
                scope=ScopeEnum.SYSTEM,
            )
        ],
    )
    # Provider 2 crashes
    p2 = FakeProvider("provider2", [], should_fail=True)

    orch = InventoryOrchestrator(providers=[p1, p2], include_manual=False)
    snapshot = orch.scan_all()

    # The crash in provider 2 must NOT prevent provider 1's results from being returned!
    assert snapshot.total_count >= 1
    assert any(r.name == "App One" for r in snapshot.records)
    assert "provider2" in snapshot.provider_errors


def test_orchestrator_duplicate_annotation():
    # Same app name in Flatpak and RPM
    r1 = InstallationRecord(
        id="flatpak:sys:org.test.App",
        name="Test App",
        package_id="org.test.App",
        source=SourceEnum.FLATPAK,
        scope=ScopeEnum.SYSTEM,
    )
    r2 = InstallationRecord(
        id="rpm:sys:test-app",
        name="Test App",
        package_id="test-app",
        source=SourceEnum.RPM,
        scope=ScopeEnum.SYSTEM,
    )
    p = FakeProvider("fake", [r1, r2])
    orch = InventoryOrchestrator(providers=[p], include_manual=False)
    snapshot = orch.scan_all()

    assert snapshot.total_count == 2
    # Verify records were NOT merged into one ambiguous record
    assert len([r for r in snapshot.records if r.name == "Test App"]) == 2
    # Verify duplicate warning was added
    assert any("Multiple installations found" in w for w in snapshot.records[0].warnings)
