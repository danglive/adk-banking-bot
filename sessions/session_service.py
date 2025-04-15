# sessions/session_service.py
from google.adk.sessions import Session
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import time
import os
import json
import sqlite3
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionService(ABC):
    """Abstract base class for different session service implementations."""

    @abstractmethod
    def create_session(self, app_name: str, user_id: str, session_id: str, state: Optional[Dict[str, Any]] = None) -> Session:
        pass

    @abstractmethod
    def get_session(self, app_name: str, user_id: str, session_id: str) -> Optional[Session]:
        pass

    @abstractmethod
    def update_session(self, session: Session) -> None:
        pass

    @abstractmethod
    def delete_session(self, app_name: str, user_id: str, session_id: str) -> None:
        pass

    @abstractmethod
    def list_sessions(self, app_name: str, user_id: str) -> List[Session]:
        pass

class BankingSessionService(SessionService):
    """Marker interface for session services used in banking bot."""
    pass

class EnhancedInMemorySessionService(BankingSessionService):
    """
    In-memory session service with tracking, TTL, and background cleanup.
    """
    def __init__(self, session_ttl: int = 3600):
        self.sessions = {}
        self.session_ttl = session_ttl
        self.session_access_times = {}
        self.session_stats = {"created": 0, "updated": 0, "accessed": 0, "deleted": 0, "expired": 0}
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
        self._cleanup_thread.start()

    def create_session(self, app_name, user_id, session_id, state=None):
        session = Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state or {},
            last_update_time=time.time()
        )
        self.sessions.setdefault(app_name, {}).setdefault(user_id, {})[session_id] = session
        self._update_access_time(app_name, user_id, session_id)
        self.session_stats["created"] += 1
        logger.info(f"Created session: {app_name}/{user_id}/{session_id}")
        return session

    def get_session(self, app_name, user_id, session_id):
        session = self.sessions.get(app_name, {}).get(user_id, {}).get(session_id)
        if session:
            self._update_access_time(app_name, user_id, session_id)
            self.session_stats["accessed"] += 1
            logger.debug(f"Accessed session: {app_name}/{user_id}/{session_id}")
        return session

    def update_session(self, session):
        self.sessions[session.app_name][session.user_id][session.id] = session
        self._update_access_time(session.app_name, session.user_id, session.id)
        self.session_stats["updated"] += 1
        logger.debug(f"Updated session: {session.app_name}/{session.user_id}/{session.id}")

    def delete_session(self, app_name, user_id, session_id):
        if self._session_exists(app_name, user_id, session_id):
            del self.sessions[app_name][user_id][session_id]
            self.session_access_times.pop((app_name, user_id, session_id), None)
            self.session_stats["deleted"] += 1
            logger.info(f"Deleted session: {app_name}/{user_id}/{session_id}")

    def list_sessions(self, app_name, user_id):
        return list(self.sessions.get(app_name, {}).get(user_id, {}).values())

    def get_stats(self):
        active_sessions = sum(len(user) for app in self.sessions.values() for user in app.values())
        return {**self.session_stats, "active_sessions": active_sessions}

    def _update_access_time(self, app_name, user_id, session_id):
        self.session_access_times[(app_name, user_id, session_id)] = time.time()

    def _session_exists(self, app_name, user_id, session_id):
        return session_id in self.sessions.get(app_name, {}).get(user_id, {})

    def _cleanup_expired_sessions(self):
        while True:
            try:
                now = time.time()
                expired = [(a, u, s) for (a, u, s), t in self.session_access_times.items() if now - t > self.session_ttl]
                for app_name, user_id, session_id in expired:
                    if self._session_exists(app_name, user_id, session_id):
                        del self.sessions[app_name][user_id][session_id]
                        self.session_access_times.pop((app_name, user_id, session_id), None)
                        self.session_stats["expired"] += 1
                        logger.info(f"Expired session: {app_name}/{user_id}/{session_id}")
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
                time.sleep(60)

class SqliteSessionService(BankingSessionService):
    """
    Persistent session service backed by SQLite.
    """
    def __init__(self, db_path: str = "banking_sessions.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS sessions (
            app_name TEXT,
            user_id TEXT,
            session_id TEXT,
            state TEXT,
            last_update_time REAL,
            PRIMARY KEY (app_name, user_id, session_id))''')
        cursor.execute('''CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (app_name, user_id)''')
        conn.commit()
        conn.close()
        logger.info(f"Initialized SQLite session database at {self.db_path}")

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def create_session(self, app_name, user_id, session_id, state=None):
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.time()
        state_json = json.dumps(state or {})
        try:
            cursor.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", (app_name, user_id, session_id, state_json, now))
            conn.commit()
            logger.info(f"Created session in DB: {app_name}/{user_id}/{session_id}")
        except sqlite3.IntegrityError:
            cursor.execute("UPDATE sessions SET state = ?, last_update_time = ? WHERE app_name = ? AND user_id = ? AND session_id = ?", (state_json, now, app_name, user_id, session_id))
            conn.commit()
            logger.warning(f"Session already exists, updated instead: {app_name}/{user_id}/{session_id}")
        finally:
            conn.close()
        return Session(id=session_id, app_name=app_name, user_id=user_id, state=state or {}, last_update_time=now)

    def get_session(self, app_name, user_id, session_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT state, last_update_time FROM sessions WHERE app_name = ? AND user_id = ? AND session_id = ?", (app_name, user_id, session_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            state_json, ts = row
            return Session(id=session_id, app_name=app_name, user_id=user_id, state=json.loads(state_json), last_update_time=ts)
        return None

    def update_session(self, session):
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.time()
        state_json = json.dumps(session.state or {})
        cursor.execute("UPDATE sessions SET state = ?, last_update_time = ? WHERE app_name = ? AND user_id = ? AND session_id = ?", (state_json, now, session.app_name, session.user_id, session.id))
        if cursor.rowcount == 0:
            cursor.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", (session.app_name, session.user_id, session.id, state_json, now))
        conn.commit()
        conn.close()

    def delete_session(self, app_name, user_id, session_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE app_name = ? AND user_id = ? AND session_id = ?", (app_name, user_id, session_id))
        conn.commit()
        conn.close()

    def list_sessions(self, app_name, user_id):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT session_id, state, last_update_time FROM sessions WHERE app_name = ? AND user_id = ?", (app_name, user_id))
        rows = cursor.fetchall()
        conn.close()
        return [Session(id=session_id, app_name=app_name, user_id=user_id, state=json.loads(state_json), last_update_time=ts) for session_id, state_json, ts in rows]

    def cleanup_old_sessions(self, max_age_seconds: int = 86400):
        conn = self._get_connection()
        cursor = conn.cursor()
        cutoff = time.time() - max_age_seconds
        cursor.execute("DELETE FROM sessions WHERE last_update_time < ?", (cutoff,))
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count

class SessionFactory:
    @staticmethod
    def create_session_service(service_type: str = "memory", **kwargs) -> BankingSessionService:
        if service_type.lower() == "memory":
            return EnhancedInMemorySessionService(kwargs.get("session_ttl", 3600))
        elif service_type.lower() == "sqlite":
            return SqliteSessionService(kwargs.get("db_path", "banking_sessions.db"))
        raise ValueError(f"Unsupported session service type: {service_type}")