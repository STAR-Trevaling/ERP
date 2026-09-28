import logging
import httpx
from typing import Any, Dict, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class OdooRPCError(Exception):
    def __init__(self, code: str, message: str, raw_data: Optional[Dict] = None):
        self.code = code
        self.message = message
        self.raw_data = raw_data
        super().__init__(f"[{code}] {message}")


class AsyncOdooClient:
    """
    Client kết nối JSON-RPC bất đồng bộ (Non-blocking Async) tới Odoo 18.
    Sử dụng endpoint chuẩn /jsonrpc với API key / User Token.
    """

    def __init__(self):
        self.url = f"{settings.ODOO_URL.rstrip('/')}/jsonrpc"
        self.db = settings.ODOO_DB
        self.username = settings.ODOO_USER
        self.password = settings.ODOO_API_KEY
        self._uid: Optional[int] = None
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def authenticate(self) -> int:
        """Đăng nhập hoặc lấy UID của user Odoo"""
        if self._uid is not None:
            return self._uid

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "authenticate",
                "args": [self.db, self.username, self.password, {}]
            },
            "id": 1
        }

        try:
            response = await self._http_client.post(self.url, json=payload)
            data = response.json()
            if "error" in data:
                err_msg = data["error"].get("data", {}).get("message", "Authentication Failed")
                logger.error(f"[ODOO-RPC] Auth error: {err_msg}")
                raise OdooRPCError("AUTH_ERROR", err_msg, data["error"])

            uid = data.get("result")
            if not uid:
                raise OdooRPCError("AUTH_REJECTED", "Sai thông tin ODOO_USER hoặc ODOO_API_KEY")

            self._uid = uid
            logger.info(f"[ODOO-RPC] Authenticated successfully as UID {uid}")
            return uid
        except httpx.RequestError as exc:
            logger.error(f"[ODOO-RPC] Network connection error: {exc}")
            raise OdooRPCError("NETWORK_ERROR", f"Không thể kết nối Odoo tại {self.url}")

    async def execute_kw(self, model: str, method: str, args: List[Any], kwargs: Optional[Dict[str, Any]] = None) -> Any:
        """Gọi execute_kw trên model của Odoo"""
        uid = await self.authenticate()
        if kwargs is None:
            kwargs = {}

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [self.db, uid, self.password, model, method, args, kwargs]
            },
            "id": 2
        }

        try:
            response = await self._http_client.post(self.url, json=payload)
            data = response.json()
            if "error" in data:
                err_msg = data["error"].get("data", {}).get("message", "RPC Execute Error")
                logger.error(f"[ODOO-RPC] Execute {model}.{method} error: {err_msg}")
                raise OdooRPCError("EXECUTE_ERROR", err_msg, data["error"])

            return data.get("result")
        except httpx.RequestError as exc:
            logger.error(f"[ODOO-RPC] Request failed: {exc}")
            raise OdooRPCError("NETWORK_ERROR", f"Lỗi mạng khi gọi Odoo: {str(exc)}")

    async def create_web_order_atomic(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gọi atomic action trên Odoo 18 tạo đơn và khóa giữ tồn kho"""
        return await self.execute_kw(
            model="sale.order",
            method="action_create_web_order_atomic",
            args=[order_data]
        )

    async def confirm_web_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gọi action xác nhận thanh toán Webhook trên Odoo 18"""
        return await self.execute_kw(
            model="sale.order",
            method="action_confirm_web_payment",
            args=[payment_data]
        )

    async def close(self):
        await self._http_client.aclose()


odoo_client = AsyncOdooClient()
