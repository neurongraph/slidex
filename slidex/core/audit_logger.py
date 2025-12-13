"""
SQLite-based audit logger for LLM interactions.
Tracks all messages sent to and received from LLMs for full auditability.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json

from slidex.config import settings
from slidex.logging_config import logger


class AuditLogger:
    """Logs LLM interactions to SQLite database."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize audit logger with database path."""
        self.db_path = db_path or settings.audit_db_path
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the audit database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                model_name TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                input_text TEXT,
                output_text TEXT,
                metadata TEXT,
                error TEXT,
                duration_ms REAL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Create index on timestamp for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
            ON llm_audit_log(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_session 
            ON llm_audit_log(session_id)
        """)
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Audit database initialized at {self.db_path}")
    
    def log_llm_call(
        self,
        model_name: str,
        operation_type: str,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> int:
        """
        Log an LLM interaction to the audit database.
        
        Args:
            model_name: Name of the LLM model used
            operation_type: Type of operation (e.g., 'embedding', 'summary', 'chat')
            input_text: Input text sent to the LLM
            output_text: Output text received from the LLM
            session_id: Optional session identifier
            metadata: Additional metadata as dictionary
            error: Error message if operation failed
            duration_ms: Duration of the operation in milliseconds
            
        Returns:
            ID of the inserted audit log entry
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO llm_audit_log 
            (timestamp, session_id, model_name, operation_type, input_text, 
             output_text, metadata, error, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            session_id,
            model_name,
            operation_type,
            input_text,
            output_text,
            metadata_json,
            error,
            duration_ms,
        ))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.debug(
            f"Audit log entry created: id={log_id}, model={model_name}, "
            f"operation={operation_type}"
        )
        
        return log_id
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """Retrieve recent audit log entries."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM llm_audit_log 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_session_logs(self, session_id: str) -> list:
        """Retrieve all logs for a specific session."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM llm_audit_log 
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


# Global audit logger instance
audit_logger = AuditLogger()
