# tests/test_sessions/test_session_service.py
import pytest
import tempfile
import os
import time
from sessions.session_service import EnhancedInMemorySessionService, SqliteSessionService

@pytest.fixture
def temp_sqlite_db():
    """Fixture to provide a temporary SQLite database file path."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_sessions.db")
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_in_memory_session_create_and_get():
    """Test creating and retrieving sessions from in-memory service."""
    service = EnhancedInMemorySessionService()
    app_name = "test_app"
    user_id = "test_user"
    session_id = "test_session"
    state = {"foo": "bar"}

    created = service.create_session(app_name, user_id, session_id, state)
    retrieved = service.get_session(app_name, user_id, session_id)

    assert created is not None
    assert retrieved is not None
    assert retrieved.id == session_id
    assert retrieved.app_name == app_name
    assert retrieved.user_id == user_id
    assert retrieved.state["foo"] == "bar"

def test_sqlite_session_persistence(temp_sqlite_db):
    """Test SQLite session persistence."""
    app_name = "test_app"
    user_id = "test_user"
    session_id = "sqlite_test"
    state = {"alpha": "beta"}

    service = SqliteSessionService(db_path=temp_sqlite_db)
    service.create_session(app_name, user_id, session_id, state)

    new_instance = SqliteSessionService(db_path=temp_sqlite_db)
    session = new_instance.get_session(app_name, user_id, session_id)

    assert session is not None
    assert session.id == session_id
    assert session.app_name == app_name
    assert session.user_id == user_id
    assert session.state["alpha"] == "beta"