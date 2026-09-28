import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from unittest.mock import AsyncMock, patch

from app.main import app
from app.db.session import Base, get_db
from app.core.odoo_client import odoo_client
import app.api.v1.endpoints.webhooks as webhooks_endpoint

TEST_DB_FILE = "./test_ecommerce.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Patch AsyncSessionLocal trong webhooks endpoint để background task dùng chung DB
webhooks_endpoint.AsyncSessionLocal = TestSessionLocal


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Mock Odoo RPC mặc định trong test để không làm văng background tasks
    with patch.object(odoo_client, "confirm_web_payment", new=AsyncMock(return_value={"status": "success", "odoo_order_id": 1})), \
         patch.object(odoo_client, "execute_kw", new=AsyncMock(return_value=[1])):

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()
