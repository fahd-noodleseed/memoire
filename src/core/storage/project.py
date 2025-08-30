"""Project storage operations."""

import json
import sqlite3
from datetime import datetime
from typing import List, Optional

from src.logging_config import get_logger
from ...models import Project

logger = get_logger('memoire.mcp.storage')

def create_project(db_path, qdrant_client, project: Project) -> str:
    """Create a new project."""
    from .db import get_or_create_collection
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO projects 
            (id, name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            project.id, project.name, project.description,
            project.created_at.isoformat(), project.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()

        # Create Qdrant collection
        get_or_create_collection(qdrant_client, project.id)
        
        return project.id
    except Exception as e:
        logger.error(f"Error creating project {project.name}: {e}", exc_info=True)
        raise

def get_project(db_path, project_id: str) -> Optional[Project]:
    """Get project by ID."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        project = _row_to_project(row)
        return project
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}", exc_info=True)
        return None

def list_projects(db_path) -> List[Project]:
    """List all projects."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        projects = [_row_to_project(row) for row in rows]
        return projects
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return []

def count_projects(db_path) -> int:
    """Count all projects."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM projects")
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    except Exception as e:
        logger.error(f"Error counting projects: {e}", exc_info=True)
        return 0

def delete_project(db_path, qdrant_client, project_id: str):
    """Delete a project and all its data."""
    # Delete from SQLite (cascade will handle related data)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error deleting project from SQLite {project_id}: {e}", exc_info=True)

    # Delete Qdrant collection
    try:
        collection_name = f"project_{project_id.replace('-', '_')}"
        qdrant_client.delete_collection(collection_name)
    except Exception as e:
        logger.warning(f"Failed to delete Qdrant collection {collection_name}: {e}")
    
    logger.info(f"Deleted project: {project_id}")

def update_project(db_path, project: Project) -> bool:
    """Update an existing project."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update project with new data
        cursor.execute("""
            UPDATE projects 
            SET name = ?, description = ?, updated_at = ?
            WHERE id = ?
        """, (
            project.name,
            project.description,
            datetime.now().isoformat(),
            project.id
        ))
        
        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected_rows > 0:
            logger.info(f"Updated project: {project.id}")
            return True
        else:
            logger.warning(f"Project not found for update: {project.id}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating project {project.id}: {e}", exc_info=True)
        return False

def _row_to_project(row) -> Project:
    """Convert SQLite row to Project object."""
    return Project(
        id=row[0],
        name=row[1],
        description=row[2] or "",
        created_at=datetime.fromisoformat(row[3]) if row[3] else datetime.now(),
        updated_at=datetime.fromisoformat(row[4]) if row[4] else datetime.now()
    )
