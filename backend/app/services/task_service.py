from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Conversation, Project, Task, TaskEvent


class ProjectNotFoundError(Exception):
    pass


class ConversationNotFoundError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


def is_uuid(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


class TaskService:
    def resolve_project(self, session: Session, project_reference: str) -> Project:
        if is_uuid(project_reference):
            project = session.get(Project, project_reference)
            if project is None:
                raise ProjectNotFoundError(project_reference)
            return project

        project = session.scalar(
            select(Project).where(Project.code == project_reference)
        )
        if project is None:
            project = Project(code=project_reference, name=project_reference)
            session.add(project)
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
    ) -> Task:
        project = self.resolve_project(session, project_reference)

        if conversation_id is not None:
            conversation = session.get(Conversation, conversation_id)
            if conversation is None or conversation.project_id != project.id:
                raise ConversationNotFoundError(conversation_id)

        task = Task(
            project_id=project.id,
            conversation_id=conversation_id,
            prompt=prompt,
            runtime_profile=runtime_profile,
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
            },
        )
        session.commit()
        return self.get_task(session, task.id)

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
        event = TaskEvent(
            task_id=task.id,
            sequence=task.next_event_sequence,
            type=event_type,
            data=data or {},
        )
        task.next_event_sequence += 1
        session.add(event)
        session.flush()
        return event

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
