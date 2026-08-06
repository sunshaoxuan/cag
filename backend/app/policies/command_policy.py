import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    risk_level: str
    reason: str


class CommandPolicyService:
    _forbidden = (
        re.compile(r"(^|\s)(rm|rmdir)\s+(-[^\s]*r|/s)\b", re.IGNORECASE),
        re.compile(r"\bgit\s+(reset\s+--hard|clean\s+-[^\s]*f)", re.IGNORECASE),
        re.compile(r"\b(format|diskpart|cipher\s+/w)\b", re.IGNORECASE),
        re.compile(r"\b(remove-item)\b.*\b-recurse\b.*\b-force\b", re.IGNORECASE),
    )
    _safe = (
        re.compile(r"^\s*(rg|git\s+(status|diff|log|show)|pytest|python\s+-m\s+pytest)\b", re.IGNORECASE),
        re.compile(r"^\s*git\s+(clone|ls-remote|rev-parse)\b", re.IGNORECASE),
        re.compile(r"^\s*svn\s+(info|export)\b", re.IGNORECASE),
        re.compile(r"^\s*(npm|pnpm)\s+(test|run\s+(test|build|lint))\b", re.IGNORECASE),
        re.compile(r"^\s*(get-childitem|get-content|select-string)\b", re.IGNORECASE),
        re.compile(r"^\s*tesseract\s+ocr\b", re.IGNORECASE),
    )

    def evaluate(self, subject: str, request_type: str) -> PolicyDecision:
        normalized = subject.strip()
        if request_type == "file_change":
            return PolicyDecision("allow", "low", "Workspace file edits are assigned to Executor")
        if any(pattern.search(normalized) for pattern in self._forbidden):
            return PolicyDecision("deny", "critical", "Destructive command pattern is forbidden")
        if any(pattern.search(normalized) for pattern in self._safe):
            return PolicyDecision("allow", "low", "Read or verification command is allowed")
        return PolicyDecision(
            "approval_required",
            "medium",
            "Command is outside the mechanically approved command set",
        )
