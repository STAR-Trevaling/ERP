import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import engine, Base
from app.api.v1.endpoints import orders, webhooks, inventory
from app.core.odoo_client import odoo_client

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo bảng Database khi khởi động
    logger.info("[STARTUP] Initializing SQLite / PostgreSQL Database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[STARTUP] Database tables initialized.")

    yield

    # Cleanup khi tắt ứng dụng
    logger.info("[SHUTDOWN] Closing Odoo RPC client sessions...")
    await odoo_client.close()
    await engine.dispose()
    logger.info("[SHUTDOWN] Completed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Middleware kết nối Website E-commerce và Odoo 18 Core ERP",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(orders.router, prefix=f"{settings.API_V1_STR}/orders", tags=["Orders"])
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks", tags=["Webhooks"])
app.include_router(inventory.router, prefix=f"{settings.API_V1_STR}/inventory", tags=["Inventory"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION
    }
