from typing import Any, AsyncGenerator

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
import pytest

from config.config import settings
from main import app as actual_app


def _join_root_path(root_path: str, path: str) -> str:
    root = (root_path or "").rstrip("/")
    if root == "/":
        root = ""
    if not path.startswith("/"):
        path = "/" + path
    return f"{root}{path}" if root else path


@pytest.fixture
async def app():
    async with LifespanManager(actual_app):
        yield actual_app


@pytest.fixture
async def client(app) -> AsyncGenerator[AsyncClient, Any]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
def api_url():
    def _api_url(path: str) -> str:
        return _join_root_path(settings.API_ROOT_PATH, path)

    return _api_url
