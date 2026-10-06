from __future__ import annotations

import os
import socket
import time
from typing import Any, Callable

import requests


DEFAULT_API_BASE = "https://nigerflora.mabrigkorie.org"
WORKER_ENDPOINT = "/api/pharmaos-worker"


def _secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        from kaggle_secrets import UserSecretsClient
        return (UserSecretsClient().get_secret(name) or "").strip()
    except Exception:
        return ""


class PharmaOSWorkerClient:
    def __init__(self, api_base: str | None = None, token: str | None = None, worker_id: str | None = None):
        self.api_base = (api_base or os.getenv("PHARMAOS_API_BASE") or DEFAULT_API_BASE).rstrip("/")
        self.token = (token or _secret("PHARMAOS_WORKER_TOKEN")).strip()
        self.worker_id = (worker_id or os.getenv("PHARMAOS_WORKER_ID") or f"kaggle-{socket.gethostname()}").strip()[:120]
        if not self.token:
            raise RuntimeError(
                "PHARMAOS_WORKER_TOKEN is missing. Add it as a Kaggle Secret; never paste it into a public notebook cell."
            )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "X-PharmaOS-Worker-Token": self.token,
                "X-PharmaOS-Worker-Id": self.worker_id,
                "User-Agent": "MABRIG-PharmaOS-Kaggle-Worker/1.0",
            }
        )

    @property
    def endpoint(self) -> str:
        return f"{self.api_base}{WORKER_ENDPOINT}"

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(self.endpoint, json={"worker_id": self.worker_id, **payload}, timeout=30)
        response.raise_for_status()
        return response.json()

    def status(self) -> dict[str, Any]:
        return self._post({"action": "status"})

    def claim(self, lease_seconds: int = 900) -> dict[str, Any] | None:
        return self._post({"action": "claim", "lease_seconds": lease_seconds}).get("job")

    def heartbeat(self, job_id: str, lease_seconds: int = 900) -> dict[str, Any]:
        return self._post({"action": "heartbeat", "job_id": job_id, "lease_seconds": lease_seconds})

    def complete(self, job_id: str, result: dict[str, Any]) -> dict[str, Any]:
        return self._post({"action": "complete", "job_id": job_id, "result": result})

    def fail(self, job_id: str, error: str) -> dict[str, Any]:
        return self._post({"action": "fail", "job_id": job_id, "error": error[:4000]})

    def run_once(self, executor: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any] | None:
        job = self.claim()
        if not job:
            return None
        job_id = job["id"]
        try:
            result = executor(job)
            result.setdefault("worker", {})
            result["worker"].update({"worker_id": self.worker_id, "provider": "kaggle"})
            self.complete(job_id, result)
            return {"job_id": job_id, "status": "completed", "result": result}
        except Exception as exc:
            self.fail(job_id, f"{type(exc).__name__}: {exc}")
            raise

    def run_forever(
        self,
        executor: Callable[[dict[str, Any]], dict[str, Any]],
        poll_seconds: int = 20,
    ) -> None:
        print(f"PharmaOS worker {self.worker_id} connected to {self.api_base}")
        while True:
            outcome = self.run_once(executor)
            if outcome is None:
                print("No pending PharmaOS jobs.")
                time.sleep(max(5, poll_seconds))
                continue
            print(f"Completed {outcome['job_id']}")


if __name__ == "__main__":
    client = PharmaOSWorkerClient()
    print(client.status())
