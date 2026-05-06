"""Local JSON license validation helper."""

from __future__ import annotations

from datetime import date
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import uuid

from app.config import APP_NAME
from app.services.app_logging import get_logger


def _current_device_id() -> str:
    raw = f"{uuid.getnode()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class LicenseService:
    """License checks backed by ``license.json`` in the app data directory."""

    def __init__(self) -> None:
        local = os.getenv("LOCALAPPDATA")
        if not local:
            raise RuntimeError("LOCALAPPDATA is not available for license storage")
        self._app_data_dir = Path(local) / APP_NAME.replace(" ", "")
        self._license_path = self._app_data_dir / "license.json"
        self._install_marker_path = self._app_data_dir / ".install_verified"

    def _install_marker_info(self) -> dict:
        found = self._install_marker_path.is_file()
        if not found:
            get_logger().warning("Install verification marker is missing: %s", self._install_marker_path)
        return {
            "install_verified": found,
            "install_marker_path": str(self._install_marker_path),
        }

    def validate_license(self) -> dict:
        p = self._license_path
        if not p.is_file():
            return {
                "valid": False,
                "status": "expired_blocked",
                "reason": "License not found",
                **self._install_marker_info(),
            }
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except OSError:
            return {
                "valid": False,
                "status": "expired_blocked",
                "reason": "Could not read license file",
                **self._install_marker_info(),
            }
        except json.JSONDecodeError:
            return {
                "valid": False,
                "status": "expired_blocked",
                "reason": "License JSON is invalid",
                **self._install_marker_info(),
            }
        return {**self._validate_payload(data), **self._install_marker_info()}

    def get_license_info(self) -> dict:
        """Best-effort read-only details for UI display."""
        p = self._license_path
        if not p.is_file():
            return {
                "found": False,
                "expiry_date": "",
                "device_id": self.current_device_id(),
                "status": "expired_blocked",
                "reason": "License not found",
                **self._install_marker_info(),
            }
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {
                "found": True,
                "expiry_date": "",
                "device_id": self.current_device_id(),
                "status": "expired_blocked",
                "reason": "License JSON is invalid",
                **self._install_marker_info(),
            }
        result = self._validate_payload(data if isinstance(data, dict) else {})
        return {
            "found": True,
            "expiry_date": str((data or {}).get("expiry_date") or ""),
            "device_id": str((data or {}).get("device_id") or self.current_device_id()),
            "status": str(result.get("status") or "expired_blocked"),
            "reason": str(result.get("reason") or ""),
            **self._install_marker_info(),
        }

    def validate_license_file(self, source: str | Path) -> dict:
        p = Path(source)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except OSError:
            return {"valid": False, "status": "expired_blocked", "reason": "Could not read selected license file"}
        except json.JSONDecodeError:
            return {"valid": False, "status": "expired_blocked", "reason": "Selected license JSON is invalid"}
        return self._validate_payload(data)

    def current_device_id(self) -> str:
        return _current_device_id()

    def _validate_payload(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return {"valid": False, "status": "expired_blocked", "reason": "License JSON root must be an object"}

        device_id = str(data.get("device_id") or "").strip()
        expiry = str(data.get("expiry_date") or "").strip()
        signature = str(data.get("signature") or "").strip().lower()
        if not device_id or not expiry or not signature:
            return {"valid": False, "status": "expired_blocked", "reason": "License is missing required fields"}

        if device_id != _current_device_id():
            return {"valid": False, "status": "expired_blocked", "reason": "License device mismatch"}

        try:
            expiry_d = date.fromisoformat(expiry)
        except ValueError:
            return {"valid": False, "status": "expired_blocked", "reason": "License expiry date is invalid"}

        secret = (self._secret() or "").encode("utf-8")
        payload_dict = {k: v for k, v in data.items() if k != "signature"}
        payload = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
        want = hmac.new(secret, payload, hashlib.sha256).hexdigest().lower()
        if not hmac.compare_digest(signature, want):
            return {"valid": False, "status": "expired_blocked", "reason": "License signature is invalid"}

        today = date.today()
        days_left = (expiry_d - today).days
        if days_left < 0:
            # 3-day grace period after expiry.
            if days_left >= -3:
                return {
                    "valid": True,
                    "status": "expired_grace",
                    "reason": f"License expired {abs(days_left)} day(s) ago (grace period).",
                }
            return {"valid": False, "status": "expired_blocked", "reason": "License has expired"}
        if days_left <= 7:
            return {
                "valid": True,
                "status": "expiring_soon",
                "reason": f"License expires in {days_left} day(s).",
            }
        return {"valid": True, "status": "valid"}

    def _secret(self) -> str:
        import os

        return (os.getenv("SMARTSTOCK_LICENSE_HMAC_SECRET") or "").strip()

    def _persist_license_file(self, source: Path) -> None:
        """Copy a validated license JSON into the app data path (same as first activation)."""
        self._license_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, self._license_path)

    def activate_from_file(self, source: str | Path) -> None:
        if bool(self.validate_license().get("valid")):
            raise PermissionError("License is already activated on this device")
        result = self.validate_license_file(source)
        if not bool(result.get("valid")):
            raise ValueError(str(result.get("reason") or "Invalid license file"))
        self._persist_license_file(Path(source))

    def replace_license_from_file(self, source: str | Path) -> None:
        """Validate and install a license file, allowing replace while a valid license exists."""
        result = self.validate_license_file(source)
        if not bool(result.get("valid")):
            raise ValueError(str(result.get("reason") or "Invalid license file"))
        self._persist_license_file(Path(source))

