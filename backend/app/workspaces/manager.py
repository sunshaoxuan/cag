import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.projects.registry import ProjectConfig


class WorkspaceError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkspaceInfo:
    workspace_id: str
    path: Path
    commit_sha: str
    branch: str


class WorkspaceManager:
    def __init__(
        self,
        *,
        root: Path,
        git_executable: str = "git",
        prepare_timeout_seconds: int = 120,
    ) -> None:
        self._root = root.resolve()
        self._git_executable = git_executable
        self._prepare_timeout_seconds = prepare_timeout_seconds
        self._root.mkdir(parents=True, exist_ok=True)

    def prepare(
        self,
        *,
        project: ProjectConfig,
        task_id: str,
    ) -> WorkspaceInfo:
        project_root = self._root / project.physical_id_string
        workspace_path = project_root / task_id
        expected_root = self._root

        project_root.mkdir(parents=True, exist_ok=True)
        resolved_parent = workspace_path.parent.resolve()
        if not resolved_parent.is_relative_to(expected_root):
            raise WorkspaceError("Workspace path escaped the configured root")
        if workspace_path.exists():
            resolved_workspace = workspace_path.resolve()
            if not resolved_workspace.is_relative_to(expected_root):
                raise WorkspaceError(
                    "Existing workspace escaped the configured root"
                )
            if not (resolved_workspace / ".git").exists():
                raise WorkspaceError(
                    f"Existing workspace is not a Git checkout for task {task_id}"
                )
            return self._resolve_workspace(
                workspace_path=resolved_workspace,
                project=project,
                task_id=task_id,
            )

        clone_command = [
            self._git_executable,
            "clone",
            "--branch",
            project.repository.default_branch,
            "--single-branch",
            "--no-tags",
            project.repository.url,
            str(workspace_path),
        ]
        try:
            result = subprocess.run(
                clone_command,
                capture_output=True,
                text=True,
                timeout=self._prepare_timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WorkspaceError(f"Git clone could not start: {exc}") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            raise WorkspaceError(f"Git clone failed: {detail[-2000:]}")

        return self._resolve_workspace(
            workspace_path=workspace_path.resolve(),
            project=project,
            task_id=task_id,
        )

    def _resolve_workspace(
        self,
        *,
        workspace_path: Path,
        project: ProjectConfig,
        task_id: str,
    ) -> WorkspaceInfo:
        commit_result = subprocess.run(
            [self._git_executable, "-C", str(workspace_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if commit_result.returncode != 0:
            raise WorkspaceError("Cloned workspace has no resolvable HEAD")

        workspace_id = f"{project.physical_id_string}/{task_id}"
        return WorkspaceInfo(
            workspace_id=workspace_id,
            path=workspace_path,
            commit_sha=commit_result.stdout.strip(),
            branch=project.repository.default_branch,
        )
