"""Fragment storage operations."""

import json
import sqlite3
from datetime import datetime
from typing import List, Optional

from src.logging_config import get_logger

from qdrant_client.http.models import PointStruct
from ...models import MemoryFragment
from ...config import config

logger = get_logger('memoire.mcp.storage')

def store_fragment(db_path, qdrant_client, fragment: MemoryFragment, embedding: List[float]) -> str:
    """Store fragment in both SQLite and Qdrant."""
    from .db import get_or_create_collection
    
    try:
        # Store metadata in SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO fragments 
            (id, project_id, content, category, tags, source, 
             context_ids, anchor_ids, custom_fields, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fragment.id, fragment.project_id, fragment.content,
            fragment.category, json.dumps(fragment.tags), fragment.source,
            json.dumps(fragment.context_ids), json.dumps(fragment.anchor_ids),
            json.dumps(fragment.custom_fields), fragment.created_at.isoformat(), fragment.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()

        # Store embedding in Qdrant
        collection_name = get_or_create_collection(qdrant_client, fragment.project_id)
        
        # Prepare payload for rich filtering capabilities
        payload = {
            "fragment_id": fragment.id,
            "project_id": fragment.project_id,
            "category": fragment.category,
            "tags": fragment.tags,
            "source": fragment.source,
            "content_preview": fragment.content[:200],  # For quick reference
            "created_at": fragment.created_at.isoformat(),
            **fragment.custom_fields  # Merge custom fields directly
        }

        point = PointStruct(
            id=fragment.id,
            vector=embedding,
            payload=payload
        )
        
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[point]
        )
        
        logger.info(f"Stored fragment: {fragment.id} in project {fragment.project_id}")
        return fragment.id
    except Exception as e:
        logger.error(f"Error storing fragment {fragment.id}: {e}", exc_info=True)
        raise

def get_fragment(db_path, fragment_id: str) -> Optional[MemoryFragment]:
    """Get fragment by ID."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM fragments WHERE id = ?", (fragment_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        fragment = _row_to_fragment(row)
        return fragment
    except Exception as e:
        logger.error(f"Error getting fragment {fragment_id}: {e}", exc_info=True)
        return None

def delete_fragment(db_path, qdrant_client, fragment_id: str) -> bool:
    """Delete fragment from both SQLite and Qdrant."""
    from .db import get_or_create_collection
    
    try:
        # First get the fragment to know which project/collection it belongs to
        fragment = get_fragment(db_path, fragment_id)
        if not fragment:
            logger.warning(f"Fragment {fragment_id} not found for deletion, cannot determine project for Qdrant deletion.")
            return False
        
        # Delete from SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM fragments WHERE id = ?", (fragment_id,))
        sqlite_success = cursor.rowcount > 0
        
        conn.commit()
        conn.close()

        # Delete from Qdrant
        collection_name = get_or_create_collection(qdrant_client, fragment.project_id)
        qdrant_client.delete(
            collection_name=collection_name,
            points_selector=[fragment.id]
        )
        
        if sqlite_success:
            logger.info(f"Successfully deleted fragment: {fragment_id}")
            return True
        else:
            logger.warning(f"Fragment {fragment_id} was not found in SQLite, but Qdrant deletion was attempted.")
            return False
            
    except Exception as e:
        logger.error(f"Failed to delete fragment {fragment_id}: {e}", exc_info=True)
        return False

def delete_fragments(db_path, qdrant_client, fragment_ids: List[str], project_id: str) -> bool:
    """Delete multiple fragments from both SQLite and Qdrant."""
    if not fragment_ids:
        return True
    from .db import get_or_create_collection
    try:
        # Delete from SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in fragment_ids)
        cursor.execute(f"DELETE FROM fragments WHERE id IN ({placeholders})", fragment_ids)
        sqlite_success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        # Delete from Qdrant
        collection_name = get_or_create_collection(qdrant_client, project_id)
        qdrant_client.delete(
            collection_name=collection_name,
            points_selector=fragment_ids
        )
        
        logger.info(f"Attempted to delete {len(fragment_ids)} fragments from project {project_id}")
        return sqlite_success
    except Exception as e:
        logger.error(f"Failed to delete fragments: {e}", exc_info=True)
        return False

def list_fragments_by_project(db_path, project_id: str, limit: int = 100) -> List[MemoryFragment]:
    """List fragments for a project."""
    logger.debug(f"Entering list_fragments_by_project for project_id: {project_id}, limit: {limit}")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM fragments WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        fragments = [_row_to_fragment(row) for row in rows]
        logger.debug(f"Found {len(fragments)} fragments for project {project_id}")
        return fragments
    except Exception as e:
        logger.error(f"Error listing fragments for project {project_id}: {e}", exc_info=True)
        return []
    finally:
        logger.debug("Exiting list_fragments_by_project")

def count_fragments_by_project(db_path, project_id: str) -> int:
    """Count fragments for a project."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM fragments WHERE project_id = ?",
            (project_id,)
        )
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    except Exception as e:
        logger.error(f"Error counting fragments for project {project_id}: {e}", exc_info=True)
        return 0

def get_fragments_by_ids(db_path, fragment_ids: List[str]) -> List[MemoryFragment]:
    """Get multiple fragments by their IDs."""
    if not fragment_ids:
        return []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join('?' for _ in fragment_ids)
        query = f"SELECT * FROM fragments WHERE id IN ({placeholders})"
        
        cursor.execute(query, fragment_ids)
        rows = cursor.fetchall()
        conn.close()
        
        fragments = [_row_to_fragment(row) for row in rows]
        return fragments
    except Exception as e:
        logger.error(f"Error getting fragments by IDs: {e}", exc_info=True)
        return []

def get_fragments_by_context(db_path, context_id: str) -> List[MemoryFragment]:
    """Get all fragments that are part of a specific context."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Use json_each to properly search within the JSON array of context_ids
        cursor.execute("""
            SELECT f.*
            FROM fragments f, json_each(f.context_ids) j
            WHERE j.value = ?
        """, (context_id,))

        rows = cursor.fetchall()
        conn.close()

        fragments = [_row_to_fragment(row) for row in rows]
        return fragments
    except Exception as e:
        logger.error(f"Error getting fragments for context {context_id}: {e}", exc_info=True)
        return []

def _row_to_fragment(row) -> MemoryFragment:
    """Convert SQLite row to MemoryFragment object."""
    # No logger here as this is a pure utility function called from logged functions
    return MemoryFragment(
        id=row[0],
        project_id=row[1],
        content=row[2],
        category=row[3] or "general",
        tags=json.loads(row[4]) if row[4] else [],
        source=row[5] or "user",
        context_ids=json.loads(row[6]) if row[6] else [],
        anchor_ids=json.loads(row[7]) if row[7] else [],
        custom_fields=json.loads(row[8]) if row[8] else {},
        created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
        updated_at=datetime.fromisoformat(row[10]) if row[10] else datetime.now()
    )