from pathlib import Path
from uuid import UUID

import yaml
from pydantic import BaseModel, ConfigDict, Field


class RepositoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2048)
    default_branch: str = Field(min_length=1, max_length=255)


class WorkspaceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(default="git_clone", pattern=r"^git_clone$")


class InstructionsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    files: list[str] = Field(default_factory=lambda: ["AGENTS.md", "README.md"])


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_profile: str = "general-engineering"
    allowed_profiles: list[str] = Field(
        default_factory=lambda: ["general-engineering"]
    )


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    physical_id: UUID
    id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(default="1", min_length=1, max_length=64)
    repository: RepositoryConfig
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    instructions: InstructionsConfig = Field(default_factory=InstructionsConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    @property
    def physical_id_string(self) -> str:
        return str(self.physical_id)


class ProjectRegistryError(RuntimeError):
    pass


class ProjectRegistry:
    def __init__(self, projects_dir: Path) -> None:
        self._projects_dir = projects_dir.resolve()
        self._by_code: dict[str, ProjectConfig] = {}
        self._by_id: dict[str, ProjectConfig] = {}
        self.reload()

    def reload(self) -> None:
        if not self._projects_dir.is_dir():
            raise ProjectRegistryError(
                f"Project directory does not exist: {self._projects_dir}"
            )

        by_code: dict[str, ProjectConfig] = {}
        by_id: dict[str, ProjectConfig] = {}
        config_paths = sorted(
            [
                *self._projects_dir.glob("*.yaml"),
                *self._projects_dir.glob("*.yml"),
            ]
        )
        if not config_paths:
            raise ProjectRegistryError(
                f"No project configuration found in {self._projects_dir}"
            )

        for config_path in config_paths:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            config = ProjectConfig.model_validate(raw)
            physical_id = config.physical_id_string
            if config.id in by_code:
                raise ProjectRegistryError(
                    f"Duplicate project code: {config.id}"
                )
            if physical_id in by_id:
                raise ProjectRegistryError(
                    f"Duplicate project physical ID: {physical_id}"
                )
            by_code[config.id] = config
            by_id[physical_id] = config

        self._by_code = by_code
        self._by_id = by_id

    def list(self) -> list[ProjectConfig]:
        return sorted(self._by_code.values(), key=lambda item: item.id)

    def get_by_code(self, code: str) -> ProjectConfig | None:
        return self._by_code.get(code)

    def resolve(self, reference: str) -> ProjectConfig | None:
        return self._by_id.get(reference) or self._by_code.get(reference)
