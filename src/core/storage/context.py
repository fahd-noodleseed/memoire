"""Context storage operations."""

import json
import sqlite3
from datetime import datetime
from typing import List, Optional

from src.logging_config import get_logger
from ...models import MemoryContext

logger = get_logger('memoire.mcp.storage')

def create_context(db_path, context: MemoryContext) -> str:
    """Create a new context."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO contexts 
            (id, project_id, name, description, fragment_ids, 
             parent_context_id, child_context_ids, custom_fields, fragment_count, 
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            context.id, context.project_id, context.name,
            context.description, json.dumps(context.fragment_ids),
            context.parent_context_id, json.dumps(context.child_context_ids),
            json.dumps(context.custom_fields), context.fragment_count,
            context.created_at.isoformat(), context.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created context: {context.name} ({context.id})")
        return context.id
    except Exception as e:
        logger.error(f"Error creating context {context.name}: {e}", exc_info=True)
        raise

def get_context(db_path, context_id: str) -> Optional[MemoryContext]:
    """Get context by ID."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM contexts WHERE id = ?", (context_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        context = _row_to_context(row)
        return context
    except Exception as e:
        logger.error(f"Error getting context {context_id}: {e}", exc_info=True)
        return None

def list_contexts_by_project(db_path, project_id: str) -> List[MemoryContext]:
    """List all contexts for a project."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM contexts WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        contexts = [_row_to_context(row) for row in rows]
        return contexts
    except Exception as e:
        logger.error(f"Error listing contexts for project {project_id}: {e}", exc_info=True)
        return []

def get_contexts_by_fragment(db_path, fragment_id: str) -> List[MemoryContext]:
    """Get all contexts that contain a specific fragment."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Use json_each to properly search within the JSON array.
        # This is more robust than INSTR.
        cursor.execute("""
            SELECT c.*
            FROM contexts c, json_each(c.fragment_ids) j
            WHERE j.value = ?
        """, (fragment_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        contexts = [_row_to_context(row) for row in rows]
        return contexts
    except Exception as e:
        logger.error(f"Error getting contexts for fragment {fragment_id}: {e}", exc_info=True)
        return []

def update_context_fragments(db_path, context_id: str, fragment_ids: List[str]) -> bool:
    """Update the fragment list for a context."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE contexts 
            SET fragment_ids = ?, fragment_count = ?, updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(fragment_ids),
            len(fragment_ids),
            datetime.now().isoformat(),
            context_id
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"Updated context {context_id} with {len(fragment_ids)} fragments")
        else:
            logger.warning(f"Context {context_id} not found for fragment update.")
        return success
        
    except Exception as e:
        logger.error(f"Failed to update context fragments for {context_id}: {e}", exc_info=True)
        return False

def count_contexts_by_project(db_path, project_id: str) -> int:
    """Count contexts for a project."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM contexts WHERE project_id = ?",
            (project_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    except Exception as e:
        logger.error(f"Error counting contexts for project {project_id}: {e}", exc_info=True)
        return 0

def delete_context(db_path, qdrant_client, context_id: str) -> bool:
    """Delete a context and its associated fragments."""
    from .fragment import delete_fragments
    try:
        # Get context to find fragments and project
        context = get_context(db_path, context_id)
        if not context:
            logger.warning(f"Context {context_id} not found for deletion.")
            return False

        # Delete associated fragments if any
        if context.fragment_ids:
            logger.info(f"Deleting {len(context.fragment_ids)} fragments associated with context {context_id}")
            delete_fragments(db_path, qdrant_client, context.fragment_ids, context.project_id)

        # Delete the context itself
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contexts WHERE id = ?", (context_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if success:
            logger.info(f"Successfully deleted context: {context_id}")
        else:
            logger.warning(f"Context {context_id} not found in database for deletion.")
        
        return success
    except Exception as e:
        logger.error(f"Failed to delete context {context_id}: {e}", exc_info=True)
        return False

def _row_to_context(row) -> MemoryContext:
    """Convert SQLite row to MemoryContext object."""
    # No logger here as this is a pure utility function called from logged functions
    return MemoryContext(
        id=row[0],
        project_id=row[1],
        name=row[2],
        description=row[3],
        fragment_ids=json.loads(row[4]) if row[4] else [],
        parent_context_id=row[5],
        child_context_ids=json.loads(row[6]) if row[6] else [],
        custom_fields=json.loads(row[7]) if row[7] else {},
        fragment_count=row[8],
        created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
        updated_at=datetime.fromisoformat(row[10]) if row[10] else datetime.now()
    )
