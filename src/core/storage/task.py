"""Task storage operations."""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict

from src.logging_config import get_logger
from ...models import Task, TaskStatus

logger = get_logger('memoire.mcp.storage')

def _row_to_task(row) -> Task:
    """Convert SQLite row to Task object."""
    return Task(
        id=row[0],
        project_id=row[1],
        title=row[2],
        description=row[3],
        status=TaskStatus(row[4]),
        created_at=datetime.fromisoformat(row[5]),
        updated_at=datetime.fromisoformat(row[6])
    )

def create_task(db_path: str, task: Task) -> str:
    """Create a new task."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (id, project_id, title, description, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task.id, task.project_id, task.title, task.description, task.status.value, task.created_at.isoformat(), task.updated_at.isoformat()))
        conn.commit()
        conn.close()
        logger.info(f"Created task: {task.id}")
        return task.id
    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        raise

def get_task(db_path: str, task_id: str) -> Optional[Task]:
    """Get a task by its ID."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        return _row_to_task(row) if row else None
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}", exc_info=True)
        return None

def list_tasks_by_project(db_path: str, project_id: str, status: Optional[TaskStatus] = None) -> List[Task]:
    """List all tasks for a project, optionally filtering by status."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM tasks WHERE project_id = ? AND status = ? ORDER BY created_at DESC", (project_id, status.value))
        else:
            cursor.execute("SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        rows = cursor.fetchall()
        conn.close()
        return [_row_to_task(row) for row in rows]
    except Exception as e:
        logger.error(f"Error listing tasks for project {project_id}: {e}", exc_info=True)
        return []

def count_tasks_by_project(db_path: str, project_id: str) -> Dict[str, int]:
    """Count tasks for a project, grouped by status."""
    counts = {status.value: 0 for status in TaskStatus}
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM tasks
            WHERE project_id = ?
            GROUP BY status
        """, (project_id,))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            counts[row[0]] = row[1]
        return counts
    except Exception as e:
        logger.error(f"Error counting tasks for project {project_id}: {e}", exc_info=True)
        return counts

def update_task(db_path: str, task_id: str, title: Optional[str] = None, description: Optional[str] = None, status: Optional[TaskStatus] = None) -> bool:
    """Update a task's title, description, or status."""
    if title is None and description is None and status is None:
        return False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        fields = []
        params = []
        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if description is not None:
            fields.append("description = ?")
            params.append(description)
        if status is not None:
            fields.append("status = ?")
            params.append(status.value)
        
        fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?"
        params.append(task_id)
        
        cursor.execute(query, tuple(params))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"Updated task: {task_id}")
        return success
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}", exc_info=True)
        return False

def delete_task(db_path: str, task_id: str) -> bool:
    """Delete a task."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        if success:
            logger.info(f"Deleted task: {task_id}")
        return success
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
        return False
