"""Read, change, and restore the active Windows power plan's sleep timeout."""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Iterator
from uuid import UUID


MAX_SECONDS = 0xFFFFFFFF
MAX_MINUTES = MAX_SECONDS // 60
SLEEP_SETTING_GUID = "29f6c1db-86da-48c5-9fdb-f2b67b1f44da"
GUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
INDEX_PATTERN = re.compile(r"0x[0-9a-fA-F]{1,8}\s*$")


@dataclass(frozen=True)
class SleepTimeoutSnapshot:
    """Power plan and its exact AC/DC idle sleep timeouts, in seconds."""

    scheme_guid: str
    ac_seconds: int
    dc_seconds: int


def _run_powercfg(*args: str, capture: bool = False) -> str:
    result = subprocess.run(
        ["powercfg", *args],
        check=True,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout if capture else ""


def _active_scheme_guid() -> str:
    output = _run_powercfg("/getactivescheme", capture=True)
    match = GUID_PATTERN.search(output)
    if match is None:
        raise ValueError("Could not read the active power plan GUID from powercfg")
    return str(UUID(match.group()))


def _read_index(output: str, source: str) -> int:
    source_pattern = re.compile(rf"(?<![A-Za-z]){source}(?![A-Za-z])", re.I)
    values = [
        int(match.group(), 16)
        for line in output.splitlines()
        if source_pattern.search(line)
        if (match := INDEX_PATTERN.search(line)) is not None
    ]
    if len(values) != 1:
        raise ValueError(f"Could not read the {source.upper()} sleep timeout from powercfg")
    return values[0]


def _validate_minutes(ac_minutes: int | None, dc_minutes: int | None) -> None:
    if ac_minutes is None and dc_minutes is None:
        raise ValueError("Specify an AC or DC timeout")
    for minutes in (ac_minutes, dc_minutes):
        if minutes is not None and (type(minutes) is not int or not 0 <= minutes <= MAX_MINUTES):
            raise ValueError(f"Timeout must be an integer from 0 to {MAX_MINUTES} minutes")


def _default_snapshot_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise OSError("LOCALAPPDATA is required for the default snapshot location")
    return Path(local_app_data) / "windows-sleep-timeout-python" / "snapshot.json"


class SleepTimeoutManager:
    """Manage one saved change to a Windows power plan at a time."""

    def __init__(self, snapshot_path: str | os.PathLike[str] | None = None):
        self.snapshot_path = Path(snapshot_path) if snapshot_path is not None else _default_snapshot_path()

    def read(self) -> SleepTimeoutSnapshot:
        """Read the current plan and both timeouts without changing anything."""
        scheme_guid = _active_scheme_guid()
        output = _run_powercfg("/query", scheme_guid, "SUB_SLEEP", "STANDBYIDLE", capture=True)
        if SLEEP_SETTING_GUID not in output.lower():
            raise ValueError("powercfg did not return the sleep idle setting")
        return SleepTimeoutSnapshot(
            scheme_guid=scheme_guid,
            ac_seconds=_read_index(output, "ac"),
            dc_seconds=_read_index(output, "dc"),
        )

    def saved_snapshot(self) -> SleepTimeoutSnapshot | None:
        """Return the pending restore point, if one exists."""
        try:
            data = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, UnicodeError) as error:
            raise ValueError(f"Invalid snapshot file: {self.snapshot_path}") from error
        if not isinstance(data, dict) or set(data) != {"version", "scheme_guid", "ac_seconds", "dc_seconds"}:
            raise ValueError(f"Invalid snapshot file: {self.snapshot_path}")
        try:
            if type(data["version"]) is not int or data["version"] != 1:
                raise ValueError("Unsupported snapshot version")
            if not isinstance(data["scheme_guid"], str):
                raise ValueError("Invalid power plan GUID")
            scheme_guid = str(UUID(data["scheme_guid"]))
            if any(type(data[name]) is not int or not 0 <= data[name] <= MAX_SECONDS for name in ("ac_seconds", "dc_seconds")):
                raise ValueError("Invalid sleep timeout")
        except (TypeError, AttributeError, ValueError) as error:
            raise ValueError(f"Invalid snapshot file: {self.snapshot_path}") from error
        return SleepTimeoutSnapshot(scheme_guid, data["ac_seconds"], data["dc_seconds"])

    def _save_snapshot(self, snapshot: SleepTimeoutSnapshot) -> None:
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.snapshot_path.parent, suffix=".tmp", delete=False
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump({"version": 1, **asdict(snapshot)}, temporary)
                temporary.write("\n")
            os.replace(temporary_path, self.snapshot_path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _write_timeout(snapshot: SleepTimeoutSnapshot, ac_seconds: int | None, dc_seconds: int | None) -> None:
        if ac_seconds is not None:
            _run_powercfg("/setacvalueindex", snapshot.scheme_guid, "SUB_SLEEP", "STANDBYIDLE", str(ac_seconds))
        if dc_seconds is not None:
            _run_powercfg("/setdcvalueindex", snapshot.scheme_guid, "SUB_SLEEP", "STANDBYIDLE", str(dc_seconds))
        if _active_scheme_guid() == snapshot.scheme_guid:
            _run_powercfg("/setactive", snapshot.scheme_guid)

    def set(self, ac_minutes: int | None = None, dc_minutes: int | None = None) -> SleepTimeoutSnapshot:
        """Save the original settings once, then change selected timeouts."""
        _validate_minutes(ac_minutes, dc_minutes)
        current = self.read()
        saved = self.saved_snapshot()
        if saved is None:
            self._save_snapshot(current)
        elif saved.scheme_guid != current.scheme_guid:
            raise RuntimeError("A restore point exists for another power plan; restore it first")
        self._write_timeout(
            current,
            None if ac_minutes is None else ac_minutes * 60,
            None if dc_minutes is None else dc_minutes * 60,
        )
        return current

    def restore(self) -> SleepTimeoutSnapshot:
        """Restore both exact values and remove the restore point on success."""
        saved = self.saved_snapshot()
        if saved is None:
            raise FileNotFoundError(f"No saved sleep timeout settings: {self.snapshot_path}")
        self._write_timeout(saved, saved.ac_seconds, saved.dc_seconds)
        self.snapshot_path.unlink()
        return saved

    @contextmanager
    def temporary(self, ac_minutes: int | None = None, dc_minutes: int | None = None) -> Iterator["SleepTimeoutManager"]:
        """Apply a temporary change and restore it on leaving the with block."""
        if self.saved_snapshot() is not None:
            raise RuntimeError("A restore point already exists; restore it before a temporary change")
        self.set(ac_minutes, dc_minutes)
        try:
            yield self
        finally:
            self.restore()


def set_sleep_timeout(ac_minutes: int | None = None, dc_minutes: int | None = None) -> None:
    """Set the active power plan's idle sleep timeout (0 means never)."""
    SleepTimeoutManager().set(ac_minutes, dc_minutes)
