import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db


# Test database setup
SQLALCHEMY_TEST_DATABASE_URL = 'sqlite:///./test.db'
test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _is_unit_test_without_app_wiring(nodeid: str) -> bool:
    return (
        'integration' in nodeid
        or 'workflow' in nodeid
        or 'tests/services/' in nodeid
        or 'tests/core/' in nodeid
    )


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope='session', autouse=True)
def setup_database(request):
    """Create all database tables before running tests."""
    # Skip for pure unit tests which have their own setup needs
    if _is_unit_test_without_app_wiring(request.node.nodeid):
        yield
        return
    
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def override_dependencies(request):
    """Override FastAPI dependencies to use test database."""
    # Skip for pure unit tests which do not need app wiring
    if _is_unit_test_without_app_wiring(request.node.nodeid):
        yield
        return
        
    from app.main import app
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(scope='session')
def anyio_backend():
    return 'asyncio'
