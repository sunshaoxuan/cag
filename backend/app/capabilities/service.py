from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from sqlalchemy import select

from app.database import Database
from app.models import (
    CapabilityAsset,
    CapabilityEvaluation,
    CapabilityPromotion,
    CapabilityRollback,
    GardenerRun,
    StandardControl,
)
from app.models.base import utc_now


REQUIRED_DEFINITION_FIELDS = {
    "trigger",
    "input_schema",
    "output_schema",
    "permissions",
    "dependencies",
    "timeout_seconds",
    "evidence_requirements",
    "acceptance",
    "rollback",
}
ALLOWED_KINDS = {"skill", "tool", "validator", "harness_profile", "memory"}
PROMOTION_ORDER = ("proposed", "validated", "benchmarked", "shadow", "canary", "active")
SENSITIVE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)(api[_ -]?key|secret|password)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(raw_prompt|customer_id|tenant_id|private_path)\b"),
)


def _definition_hash(kind: str, code: str, version: str, definition: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"kind": kind, "code": code, "version": version, "definition": definition},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


class CapabilityService:
    def __init__(
        self,
        database: Database,
        self_improvement_root: Path | None,
    ) -> None:
        self._database = database
        self._root = self_improvement_root

    def seed_defaults(self) -> None:
        for kind, code in (
            ("skill", "repository-map"),
            ("skill", "call-chain-tracing"),
            ("skill", "version-difference-investigation"),
            ("skill", "evidence-package"),
            ("skill", "rag-query-planning"),
            ("skill", "citation-answering"),
            ("skill", "cross-tenant-redaction"),
            ("skill", "failure-postmortem"),
            ("tool", "git-analysis"),
            ("tool", "ast-symbol-graph"),
            ("tool", "pgvector-hybrid-search"),
            ("tool", "ollama-embedding-rerank"),
            ("tool", "test-build-runner"),
            ("validator", "secret-scanner"),
            ("validator", "prompt-injection-scanner"),
            ("validator", "citation-verifier"),
            ("validator", "groundedness-evaluator"),
            ("harness_profile", "balanced-engineering"),
        ):
            definition = self.default_definition(kind, code)
            self.propose(
                kind=kind,
                code=code,
                version="1.0.0",
                definition=definition,
                source="gateway-seed",
            )
        self._seed_controls()

    @staticmethod
    def default_definition(kind: str, code: str) -> dict[str, Any]:
        return {
            "trigger": {"task_types": [code], "minimum_confidence": 0.8},
            "input_schema": {"type": "object", "additionalProperties": False},
            "output_schema": {"type": "object"},
            "permissions": ["read_workspace"],
            "dependencies": [],
            "timeout_seconds": 900,
            "evidence_requirements": ["source_path", "validation_result"],
            "acceptance": {
                "security_pass_rate": 1.0,
                "architecture_pass_rate": 1.0,
                "quality_gain_percent": 5.0,
            },
            "rollback": {
                "method": "registry_status_restore",
                "target_status": "benchmarked",
            },
            "kind": kind,
        }

    def propose(
        self,
        *,
        kind: str,
        code: str,
        version: str,
        definition: dict[str, Any],
        source: str = "learning-pipeline",
    ) -> CapabilityAsset:
        if kind not in ALLOWED_KINDS:
            raise ValueError(f"Unsupported capability kind: {kind}")
        content_hash = _definition_hash(kind, code, version, definition)
        with self._database.session_factory() as session:
            existing = session.scalar(
                select(CapabilityAsset).where(
                    CapabilityAsset.content_hash == content_hash
                )
            )
            if existing is not None:
                return existing
            asset = CapabilityAsset(
                kind=kind,
                code=code,
                version=version,
                status="proposed",
                definition=definition,
                content_hash=content_hash,
                source=source,
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
            return asset

    def list_assets(self, kind: str | None = None) -> list[CapabilityAsset]:
        with self._database.session_factory() as session:
            statement = select(CapabilityAsset).order_by(
                CapabilityAsset.kind, CapabilityAsset.code, CapabilityAsset.created_at.desc()
            )
            if kind is not None:
                statement = statement.where(CapabilityAsset.kind == kind)
            return list(session.scalars(statement))

    def get_asset(self, asset_id: str) -> CapabilityAsset:
        with self._database.session_factory() as session:
            asset = session.get(CapabilityAsset, asset_id)
            if asset is None:
                raise KeyError(asset_id)
            return asset

    def evaluate(
        self,
        asset_id: str,
        metrics: dict[str, Any],
    ) -> CapabilityEvaluation:
        with self._database.session_factory() as session:
            asset = session.get(CapabilityAsset, asset_id)
            if asset is None:
                raise KeyError(asset_id)
            findings = self._governance_findings(asset.definition)
            replay_count = int(metrics.get("replay_count", 0))
            project_coverage = int(metrics.get("project_coverage", 0))
            gates = {
                "schema": not findings,
                "dependencies": bool(metrics.get("dependencies_passed", False)),
                "permissions": bool(metrics.get("permissions_passed", False)),
                "supply_chain": bool(metrics.get("supply_chain_passed", False)),
                "security": float(metrics.get("security_pass_rate", 0)) == 1.0,
                "architecture": float(metrics.get("architecture_pass_rate", 0)) == 1.0,
                "replays": replay_count >= 20 and project_coverage >= 2,
                "critical_accuracy": not bool(metrics.get("critical_accuracy_regression", True)),
                "quality_gain": float(metrics.get("quality_gain_percent", 0)) >= 5.0,
                "success_rate": float(metrics.get("candidate_success_rate", 0))
                >= float(metrics.get("baseline_success_rate", 1)),
                "latency": float(metrics.get("p95_time_increase_percent", 100)) <= 10.0
                or bool(metrics.get("weighted_quality_override", False)),
            }
            passed = all(gates.values())
            evaluation = CapabilityEvaluation(
                asset_id=asset.id,
                stage="benchmark",
                passed=passed,
                replay_count=replay_count,
                project_coverage=project_coverage,
                metrics={**metrics, "gates": gates},
                findings=findings,
            )
            session.add(evaluation)
            session.flush()
            if passed:
                self._transition(session, asset, "validated", {"evaluation_id": evaluation.id})
                self._transition(session, asset, "benchmarked", {"evaluation_id": evaluation.id})
            session.commit()
            session.refresh(evaluation)
            return evaluation

    def record_shadow(
        self, asset_id: str, *, passed: bool, metrics: dict[str, Any] | None = None
    ) -> CapabilityAsset:
        return self._record_rollout(asset_id, "shadow", passed, metrics or {})

    def record_canary(
        self, asset_id: str, *, passed: bool, metrics: dict[str, Any] | None = None
    ) -> CapabilityAsset:
        return self._record_rollout(asset_id, "canary", passed, metrics or {})

    def _record_rollout(
        self,
        asset_id: str,
        stage: str,
        passed: bool,
        metrics: dict[str, Any],
    ) -> CapabilityAsset:
        with self._database.session_factory() as session:
            asset = session.get(CapabilityAsset, asset_id)
            if asset is None:
                raise KeyError(asset_id)
            if stage == "shadow" and asset.status not in {"benchmarked", "shadow"}:
                raise ValueError("Shadow requires a benchmarked asset")
            if stage == "canary" and asset.status not in {"canary"}:
                raise ValueError("Canary requires ten successful shadow runs")
            evaluation = CapabilityEvaluation(
                asset_id=asset.id,
                stage=stage,
                passed=passed,
                replay_count=1,
                project_coverage=int(metrics.get("project_coverage", 1)),
                metrics=metrics,
                findings=[] if passed else [{"code": f"{stage}_failure"}],
            )
            session.add(evaluation)
            if passed:
                asset.consecutive_failures = 0
                if stage == "shadow":
                    if asset.status == "benchmarked":
                        self._transition(session, asset, "shadow", {"run": 1})
                    asset.shadow_runs += 1
                    if asset.shadow_runs >= 10:
                        self._transition(
                            session, asset, "canary", {"shadow_runs": asset.shadow_runs}
                        )
                else:
                    asset.canary_runs += 1
                    if asset.canary_runs >= 5:
                        promotion = self._transition(
                            session, asset, "active", {"canary_runs": asset.canary_runs}
                        )
                        asset.active = True
                        promotion.receipt_path = self._write_receipt(
                            asset, "installation", promotion.evidence
                        )
            else:
                asset.consecutive_failures += 1
                if asset.consecutive_failures >= 2:
                    self._rollback_in_session(
                        session, asset, f"Two consecutive {stage} failures"
                    )
            quality_delta = float(metrics.get("quality_delta_percent", 0))
            asset.rolling_quality_delta = quality_delta
            if quality_delta < -5:
                self._rollback_in_session(
                    session, asset, "Rolling quality score decreased beyond five percent"
                )
            session.commit()
            session.refresh(asset)
            return asset

    def rollback(self, asset_id: str, reason: str) -> CapabilityRollback:
        with self._database.session_factory() as session:
            asset = session.get(CapabilityAsset, asset_id)
            if asset is None:
                raise KeyError(asset_id)
            rollback = self._rollback_in_session(session, asset, reason)
            session.commit()
            session.refresh(rollback)
            return rollback

    def _rollback_in_session(
        self, session: Any, asset: CapabilityAsset, reason: str
    ) -> CapabilityRollback:
        previous = asset.status
        asset.status = "benchmarked"
        asset.active = False
        asset.canary_runs = 0
        asset.consecutive_failures = 0
        rollback = CapabilityRollback(
            asset_id=asset.id,
            reason=reason,
            previous_status=previous,
            restored_status="benchmarked",
        )
        session.add(rollback)
        session.flush()
        rollback.receipt_path = self._write_receipt(
            asset, "rollback", {"reason": reason, "previous_status": previous}
        )
        return rollback

    def _transition(
        self,
        session: Any,
        asset: CapabilityAsset,
        target: str,
        evidence: dict[str, Any],
    ) -> CapabilityPromotion:
        current_index = PROMOTION_ORDER.index(asset.status)
        target_index = PROMOTION_ORDER.index(target)
        if target_index != current_index + 1:
            raise ValueError(f"Invalid promotion transition: {asset.status} to {target}")
        promotion = CapabilityPromotion(
            asset_id=asset.id,
            from_status=asset.status,
            to_status=target,
            decision="promoted",
            evidence=evidence,
        )
        session.add(promotion)
        asset.status = target
        return promotion

    def list_evaluations(self) -> list[CapabilityEvaluation]:
        with self._database.session_factory() as session:
            return list(
                session.scalars(
                    select(CapabilityEvaluation).order_by(
                        CapabilityEvaluation.created_at.desc()
                    )
                )
            )

    def list_promotions(self) -> list[CapabilityPromotion]:
        with self._database.session_factory() as session:
            return list(
                session.scalars(
                    select(CapabilityPromotion).order_by(
                        CapabilityPromotion.created_at.desc()
                    )
                )
            )

    def list_rollbacks(self) -> list[CapabilityRollback]:
        with self._database.session_factory() as session:
            return list(
                session.scalars(
                    select(CapabilityRollback).order_by(
                        CapabilityRollback.created_at.desc()
                    )
                )
            )

    def run_gardeners(self) -> list[GardenerRun]:
        results: list[GardenerRun] = []
        with self._database.session_factory() as session:
            for gardener in ("doc", "skill", "tool", "memory"):
                duplicate_count = len(
                    list(
                        session.scalars(
                            select(CapabilityAsset).where(
                                CapabilityAsset.kind == gardener
                                if gardener in ALLOWED_KINDS
                                else CapabilityAsset.kind == "memory"
                            )
                        )
                    )
                )
                run = GardenerRun(
                    gardener=f"{gardener}-gardener",
                    status="completed",
                    findings=[{"code": "asset_inventory", "count": duplicate_count}],
                    actions=[],
                    completed_at=utc_now(),
                )
                session.add(run)
                results.append(run)
            session.commit()
            for result in results:
                session.refresh(result)
        return results

    def list_controls(self) -> list[StandardControl]:
        with self._database.session_factory() as session:
            return list(
                session.scalars(
                    select(StandardControl).order_by(
                        StandardControl.framework, StandardControl.code
                    )
                )
            )

    @staticmethod
    def _governance_findings(definition: dict[str, Any]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        missing = sorted(REQUIRED_DEFINITION_FIELDS - set(definition))
        if missing:
            findings.append({"code": "schema_missing_fields", "fields": missing})
        payload = json.dumps(definition, ensure_ascii=False)
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(payload):
                findings.append({"code": "sensitive_content", "pattern": pattern.pattern})
        return findings

    def _write_receipt(
        self,
        asset: CapabilityAsset,
        action: str,
        evidence: dict[str, Any],
    ) -> str | None:
        if self._root is None:
            return None
        receipt_root = self._root / "installation-receipts"
        receipt_root.mkdir(parents=True, exist_ok=True)
        path = receipt_root / f"{asset.code}-{asset.version}-{action}-{asset.id}.json"
        payload = {
            "action": action,
            "asset_id": asset.id,
            "kind": asset.kind,
            "code": asset.code,
            "version": asset.version,
            "content_hash": asset.content_hash,
            "source": asset.source,
            "scope": "current-agent-gateway",
            "evidence": evidence,
            "validation": "capability promotion policy",
            "rollback": asset.definition.get("rollback"),
            "created_at": utc_now().isoformat(),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(path)

    def _seed_controls(self) -> None:
        controls = (
            ("RAG-01", "NeurIPS RAG", "Non-parametric evidence retrieval"),
            ("AIMS-01", "ISO/IEC 42001:2023", "AI management and continual improvement"),
            ("RISK-01", "ISO/IEC 23894:2023", "AI risk treatment"),
            ("RMF-01", "NIST AI RMF", "Govern, map, measure and manage"),
            ("DQ-01", "ISO/IEC 5259", "Knowledge data quality"),
            ("ISMS-01", "ISO/IEC 27001:2022", "Enterprise knowledge security"),
            ("LLM-01", "OWASP LLM Top 10", "Prompt injection and tool control"),
        )
        with self._database.session_factory() as session:
            for code, framework, title in controls:
                if session.scalar(
                    select(StandardControl).where(StandardControl.code == code)
                ) is not None:
                    continue
                session.add(
                    StandardControl(
                        code=code,
                        framework=framework,
                        title=title,
                        implementation_status="mapped",
                        control_mapping={"scope": "control evidence mapping"},
                        evidence_paths=[
                            "docs/standards-control-matrix.md",
                            "docs/evidence/evidence_index.md",
                        ],
                        certification_claimed=False,
                    )
                )
            session.commit()
