"""Database initialization and common operations."""

import sqlite3
from pathlib import Path
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams

from src.logging_config import get_logger
from ...config import config

logger = get_logger('memoire.mcp.storage')

def init_sqlite(db_path):
    """Create SQLite tables if they don't exist."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fragments (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                tags TEXT,  -- JSON array
                source TEXT DEFAULT 'user',
                context_ids TEXT,  -- JSON array
                anchor_ids TEXT,   -- JSON array
                custom_fields TEXT,  -- JSON object
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                fragment_ids TEXT,  -- JSON array
                parent_context_id TEXT,
                child_context_ids TEXT,  -- JSON array
                custom_fields TEXT,  -- JSON object
                fragment_count INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (parent_context_id) REFERENCES contexts (id) ON DELETE SET NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anchors (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                fragment_ids TEXT,  -- JSON array
                context_ids TEXT,   -- JSON array
                tags TEXT,          -- JSON array
                access_count INTEGER DEFAULT 0,
                custom_fields TEXT,  -- JSON object
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                last_accessed TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fragments_project ON fragments (project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fragments_category ON fragments (category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contexts_project ON contexts (project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_anchors_project ON anchors (project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks (project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status)")
        
        conn.commit()
        conn.close()
        
        logger.info("SQLite database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing SQLite database at {db_path}: {e}", exc_info=True)
        raise

def get_or_create_collection(qdrant_client, project_id):
    """Get or create Qdrant collection for a project."""
    collection_name = f"project_{project_id.replace('-', '_')}"

    # Get Qdrant config values
    hnsw_m = config.get("storage.qdrant.hnsw_m", 16)
    hnsw_ef_construct = config.get("storage.qdrant.hnsw_ef_construct", 100)
    optimizers_default_segment_number = config.get("storage.qdrant.optimizers_default_segment_number", 2)
    
    # Get embedding dimension from config
    embedding_dimension = config.get("embedding.dimension", 768)

    try:
        # Try to get existing collection
        collection_info = qdrant_client.get_collection(collection_name)
    except Exception:
        # Create new collection with optimized settings
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=embedding_dimension,  # Use dimension from config
                distance=Distance.COSINE,
            ),
            # Optimizations for better performance
            hnsw_config=models.HnswConfigDiff(
                m=hnsw_m,  # Number of bi-directional links for every new element during construction
                ef_construct=hnsw_ef_construct,  # Size of the dynamic candidate list
            ),
            optimizers_config=models.OptimizersConfigDiff(
                default_segment_number=optimizers_default_segment_number,  # Number of segments to optimize
            ),
        )
        logger.info(f"Created new collection: {collection_name}")
    
    return collection_name