import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
from threading import Lock

QUOTA_FILE = Path("/app/.api-quotas.json")

DAILY_LIMITS = {
    "groq": 1000,
    "openrouter": 1000,
    "gemini": 1500,
}

MONTHLY_LIMITS = {
    "tavily": 1000,
    "brave": 2000,
}

WARN_THRESHOLD = 80
BLOCK_THRESHOLD = 95


class QuotaManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._file_lock = Lock()
        self._init_quota_file()

    def _init_quota_file(self):
        if not QUOTA_FILE.exists():
            data = {
                "daily": {name: {"used": 0, "date": ""} for name in DAILY_LIMITS},
                "monthly": {name: {"used": 0, "month": ""} for name in MONTHLY_LIMITS},
                "blocked": []
            }
            self._write_data(data)

    def _read_data(self) -> Dict:
        with self._file_lock:
            if QUOTA_FILE.exists():
                return json.loads(QUOTA_FILE.read_text())
            return {"daily": {}, "monthly": {}, "blocked": []}

    def _write_data(self, data: Dict):
        with self._file_lock:
            QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
            QUOTA_FILE.write_text(json.dumps(data, indent=2))

    def _check_and_reset(self, data: Dict) -> Dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        modified = False

        for name in DAILY_LIMITS:
            if name not in data["daily"]:
                data["daily"][name] = {"used": 0, "date": ""}
            if data["daily"][name].get("date") != today:
                data["daily"][name] = {"used": 0, "date": today}
                if name in data["blocked"]:
                    data["blocked"].remove(name)
                modified = True

        for name in MONTHLY_LIMITS:
            if name not in data["monthly"]:
                data["monthly"][name] = {"used": 0, "month": ""}
            if data["monthly"][name].get("month") != this_month:
                data["monthly"][name] = {"used": 0, "month": this_month}
                if name in data["blocked"]:
                    data["blocked"].remove(name)
                modified = True

        if modified:
            self._write_data(data)
        return data

    def can_use(self, service: str) -> bool:
        data = self._read_data()
        data = self._check_and_reset(data)

        if service in data.get("blocked", []):
            return False

        if service in DAILY_LIMITS:
            used = data["daily"].get(service, {}).get("used", 0)
            limit = DAILY_LIMITS[service]
            return (used * 100 / limit) < BLOCK_THRESHOLD

        if service in MONTHLY_LIMITS:
            used = data["monthly"].get(service, {}).get("used", 0)
            limit = MONTHLY_LIMITS[service]
            return (used * 100 / limit) < BLOCK_THRESHOLD

        return True

    def use(self, service: str, amount: int = 1) -> bool:
        data = self._read_data()
        data = self._check_and_reset(data)

        if service in data.get("blocked", []):
            return False

        if service in DAILY_LIMITS:
            current = data["daily"].get(service, {}).get("used", 0)
            new_total = current + amount
            limit = DAILY_LIMITS[service]
            pct = new_total * 100 / limit

            if pct >= BLOCK_THRESHOLD:
                if "blocked" not in data:
                    data["blocked"] = []
                data["blocked"].append(service)
                self._write_data(data)
                return False

            data["daily"][service]["used"] = new_total
            self._write_data(data)
            return True

        if service in MONTHLY_LIMITS:
            current = data["monthly"].get(service, {}).get("used", 0)
            new_total = current + amount
            limit = MONTHLY_LIMITS[service]
            pct = new_total * 100 / limit

            if pct >= BLOCK_THRESHOLD:
                if "blocked" not in data:
                    data["blocked"] = []
                data["blocked"].append(service)
                self._write_data(data)
                return False

            data["monthly"][service]["used"] = new_total
            self._write_data(data)
            return True

        return True

    def get_status(self, service: str) -> Dict:
        data = self._read_data()
        data = self._check_and_reset(data)

        if service in DAILY_LIMITS:
            used = data["daily"].get(service, {}).get("used", 0)
            limit = DAILY_LIMITS[service]
            return {"used": used, "limit": limit, "remaining": limit - used, "type": "daily"}

        if service in MONTHLY_LIMITS:
            used = data["monthly"].get(service, {}).get("used", 0)
            limit = MONTHLY_LIMITS[service]
            return {"used": used, "limit": limit, "remaining": limit - used, "type": "monthly"}

        return {"used": 0, "limit": -1, "remaining": -1, "type": "unlimited"}

    def get_all_status(self) -> Dict:
        result = {}
        for service in list(DAILY_LIMITS.keys()) + list(MONTHLY_LIMITS.keys()):
            result[service] = self.get_status(service)
        return result


quota_manager = QuotaManager()
