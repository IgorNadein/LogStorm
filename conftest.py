from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--real-db",
        action="store",
        default=None,
        help="Path to a local collector events.db for optional realdb tests.",
    )


@pytest.fixture
def real_db_path(request):
    path = request.config.getoption("--real-db")
    if not path:
        pytest.skip("realdb tests require --real-db")

    db_path = Path(path)
    if not db_path.exists():
        pytest.skip(f"realdb file does not exist: {db_path}")
    return db_path
