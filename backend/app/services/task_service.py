from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Conversation,
    Product,
    ProductVersion,
    Project,
    Task,
    TaskEvent,
    TaskStatus,
    Tenant,
)
from app.projects.registry import ProjectConfig, ProjectRegistry


class ProjectNotFoundError(Exception):
    pass


class RuntimeProfileNotAllowedError(Exception):
    pass


class ConversationNotFoundError(Exception):
    pass


class ConversationBusyError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


class TaskService:
    def __init__(self, project_registry: ProjectRegistry) -> None:
        self.project_registry = project_registry

    def resolve_project(self, session: Session, project_reference: str) -> Project:
        config = self.project_registry.resolve(project_reference)
        if config is None:
            raise ProjectNotFoundError(project_reference)
        return self.sync_project(session, config)

    def sync_project(
        self,
        session: Session,
        config: ProjectConfig,
    ) -> Project:
        project = session.get(Project, config.physical_id_string)
        if project is None:
            conflicting_project = session.scalar(
                select(Project).where(Project.code == config.id)
            )
            if conflicting_project is not None:
                raise ProjectNotFoundError(
                    f"Project code {config.id} has a conflicting physical ID"
                )
            project = Project(
                id=config.physical_id_string,
                code=config.id,
                name=config.name,
            )
            session.add(project)
        project.code = config.id
        project.name = config.name
        project.repository_url = config.repository.url
        project.default_branch = config.repository.default_branch
        project.config_version = config.version
        if config.tenant is not None:
            tenant = session.scalar(
                select(Tenant).where(Tenant.code == config.tenant.code)
            )
            if tenant is None:
                tenant = Tenant(code=config.tenant.code, name=config.tenant.name)
                session.add(tenant)
                session.flush()
            tenant.name = config.tenant.name
            project.tenant_id = tenant.id
        if config.product is not None:
            product = session.scalar(
                select(Product).where(Product.code == config.product.code)
            )
            if product is None:
                product = Product(code=config.product.code, name=config.product.name)
                session.add(product)
                session.flush()
            product.name = config.product.name
            product_version = session.scalar(
                select(ProductVersion).where(
                    ProductVersion.product_id == product.id,
                    ProductVersion.version == config.product.version,
                )
            )
            if product_version is None:
                product_version = ProductVersion(
                    product_id=product.id,
                    version=config.product.version,
                )
                session.add(product_version)
                session.flush()
            project.product_version_id = product_version.id
        session.flush()
        return project

    def create_task(
        self,
        session: Session,
        *,
        project_reference: str,
        prompt: str,
        conversation_id: str | None,
        runtime_profile: str,
        knowledge_mode: str = "assist",
    ) -> Task:
        project = self.resolve_project(session, project_reference)
        project_config = self.project_registry.resolve(project_reference)
        if (
            project_config is None
            or runtime_profile not in project_config.runtime.allowed_profiles
        ):
            raise RuntimeProfileNotAllowedError(runtime_profile)

        if conversation_id is not None:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None or conversation.project_id != project.id:
                raise ConversationNotFoundError(conversation_id)
            active_task_id = session.scalar(
                select(Task.id).where(
                    Task.conversation_id == conversation_id,
                    ~Task.status.in_(TaskStatus.TERMINAL),
                )
            )
            if active_task_id is not None:
                raise ConversationBusyError(conversation_id)

        task = Task(
            project_id=project.id,
            conversation_id=conversation_id,
            prompt=prompt,
            runtime_profile=runtime_profile,
            knowledge_mode=knowledge_mode,
        )
        session.add(task)
        session.flush()
        self.append_event(
            session,
            task=task,
            event_type="task.created",
            data={
                "project_id": project.id,
                "project_code": project.code,
                "runtime_profile": runtime_profile,
                "knowledge_mode": knowledge_mode,
            },
        )
        session.commit()
        return self.get_task(session, task.id)

    def create_conversation(
        self,
        session: Session,
        *,
        project_reference: str,
        title: str | None,
    ) -> Conversation:
        project = self.resolve_project(session, project_reference)
        conversation = Conversation(project_id=project.id, title=title)
        session.add(conversation)
        session.commit()
        return self.get_conversation(session, conversation.id)

    def get_conversation(
        self,
        session: Session,
        conversation_id: str,
    ) -> Conversation:
        conversation = session.scalar(
            select(Conversation)
            .options(selectinload(Conversation.project))
            .where(Conversation.id == conversation_id)
        )
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    def get_task(self, session: Session, task_id: str) -> Task:
        task = session.scalar(
            select(Task)
            .options(selectinload(Task.project))
            .where(Task.id == task_id)
        )
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    def append_event(
        self,
        session: Session,
        *,
        task: Task,
        event_type: str,
        data: dict[str, object] | None = None,
    ) -> TaskEvent:
        conversation_sequence = None
        if task.conversation_id is not None:
            conversation = session.scalar(
                select(Conversation)
                .where(Conversation.id == task.conversation_id)
                .with_for_update()
            )
            if conversation is not None:
                conversation_sequence = conversation.next_event_sequence
                conversation.next_event_sequence += 1

        event = TaskEvent(
            task_id=task.id,
            conversation_id=task.conversation_id,
            sequence=task.next_event_sequence,
            conversation_sequence=conversation_sequence,
            type=event_type,
            data=data or {},
        )
        task.next_event_sequence += 1
        session.add(event)
        session.flush()
        return event

    def list_conversation_events(
        self,
        session: Session,
        *,
        conversation_id: str,
        after_sequence: int = 0,
    ) -> list[TaskEvent]:
        if session.get(Conversation, conversation_id) is None:
            raise ConversationNotFoundError(conversation_id)
        return list(
            session.scalars(
                select(TaskEvent)
                .where(
                    TaskEvent.conversation_id == conversation_id,
                    TaskEvent.conversation_sequence > after_sequence,
                )
                .order_by(TaskEvent.conversation_sequence)
            )
        )

    def list_conversation_tasks(
        self,
        session: Session,
        *,
        conversation_id: str,
    ) -> list[Task]:
        if session.get(Conversation, conversation_id) is None:
            raise ConversationNotFoundError(conversation_id)
        return list(
            session.scalars(
                select(Task)
                .options(selectinload(Task.project))
                .where(Task.conversation_id == conversation_id)
                .order_by(Task.created_at)
            )
        )

    def list_events(
        self,
        session: Session,
        *,
        task_id: str,
        after_sequence: int = 0,
    ) -> list[TaskEvent]:
        if session.get(Task, task_id) is None:
            raise TaskNotFoundError(task_id)
        return list(
            session.scalars(
                select(TaskEvent)
                .where(
                    TaskEvent.task_id == task_id,
                    TaskEvent.sequence > after_sequence,
                )
                .order_by(TaskEvent.sequence)
            )
        )
