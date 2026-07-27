from hashlib import sha256
import json
import re
from typing import Any

from sqlalchemy import func, select

from app.capabilities.service import CapabilityService
from app.database import Database
from app.models import LearningSignal, Task


class LearningService:
    def __init__(self, database: Database, capabilities: CapabilityService) -> None:
        self._database = database
        self._capabilities = capabilities

    def capture_task(
        self,
        *,
        task_id: str,
        mode: str,
    ) -> dict[str, Any]:
        with self._database.session_factory() as session:
            task = session.get(Task, task_id)
            if task is None:
                raise KeyError(task_id)
            normalized = re.sub(r"\s+", " ", task.prompt.strip().lower())
            task_type = " ".join(normalized.split()[:12])
            fingerprint = sha256(task_type.encode("utf-8")).hexdigest()
            report = task.final_report or {}
            success = str(report.get("status", task.status)) in {"completed", "success"}
            signal_type = "successful_pattern" if success else "failure_pattern"
            session.add(
                LearningSignal(
                    task_id=task.id,
                    signal_type=signal_type,
                    fingerprint=fingerprint,
                    payload={
                        "task_type": task_type,
                        "harness_profile": task.harness_profile,
                        "validation": report.get("validation", []),
                    },
                )
            )
            session.commit()
            threshold = 3 if success else 2
            occurrence_count = int(
                session.scalar(
                    select(func.count(LearningSignal.id)).where(
                        LearningSignal.fingerprint == fingerprint,
                        LearningSignal.signal_type == signal_type,
                    )
                )
                or 0
            )

        asset_id = None
        if occurrence_count >= threshold:
            definition = self._capabilities.default_definition(
                "skill", f"learned-{fingerprint[:12]}"
            )
            definition["trigger"] = {
                "task_type_fingerprint": fingerprint,
                "minimum_occurrences": threshold,
            }
            definition["evidence_requirements"] = [
                "learning_signal_ids",
                "task_validation",
                "cross_project_replay",
            ]
            asset = self._capabilities.propose(
                kind="skill",
                code=f"learned-{fingerprint[:12]}",
                version="0.1.0",
                definition=definition,
                source="task-learning",
            )
            asset_id = asset.id
        return {
            "signal_type": signal_type,
            "fingerprint": fingerprint,
            "occurrence_count": occurrence_count,
            "threshold": threshold,
            "candidate_asset_id": asset_id,
            "evaluation_requested": mode == "evaluate" and asset_id is not None,
        }
