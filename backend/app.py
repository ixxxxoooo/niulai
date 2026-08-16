"""FastAPI 应用入口"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .api import routes
from .datasource import eastmoney
from .db import store as db
from .db.sync import start_background_sync
from .logging_config import logger

FRONTEND_DIST = config.BASE_DIR / "frontend" / "dist"
_SKIP_SQLITE_LOG = ("/api/log/action", "/api/logs/api", "/api/logs/actions", "/api/logs/datasource")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动：初始化 SQLite + 席位标签 + 后台同步股票列表。"""
    db.init_db()
    from .db.lhb_seats import ensure_tables, init_builtin_seats, seat_count
    ensure_tables()
    if seat_count() == 0:
        init_builtin_seats()
    # 申万行业 / 东财板块表：空则后台自动同步
    import threading
    from .db.sw_industry import ensure_tables as sw_ensure, sw_count as sw_count, start_sw_sync
    from .db.sectors import ensure_tables as sec_ensure, sector_count as sec_count, sync_sectors
    sw_ensure()
    sec_ensure()
    if sw_count() == 0:
        start_sw_sync()
    if sec_count() == 0:
        threading.Thread(target=sync_sectors, daemon=True).start()
    logger.info("SQLite 已就绪 stocks=%s updated=%s seats=%s",
                db.stock_count(), db.stocks_updated_at(), seat_count())
    start_background_sync()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="牛来 niulai - A股盘面分析", version="1.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 本地自用工具
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("API %s %s 异常", request.method, request.url.path)
            raise
        dur_ms = (time.perf_counter() - start) * 1000
        path = request.url.path
        if path.startswith("/api"):
            qs = str(request.url.query or "")
            size = int(response.headers.get("content-length") or 0)
            logger.info("API %s %s%s -> %s (%.1fms)%s",
                        request.method, path,
                        f"?{qs}" if qs else "",
                        response.status_code, dur_ms,
                        f" {size}B" if size else "")
            if not any(path.startswith(p) for p in _SKIP_SQLITE_LOG):
                db.log_api(request.method, path, qs, response.status_code, dur_ms, size)
        return response

    @app.exception_handler(eastmoney.EastMoneyError)
    async def em_error_handler(request: Request, exc: eastmoney.EastMoneyError):
        """数据源节点全挂时返回 503 而非 500"""
        logger.warning("数据源不可用: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"detail": f"行情数据源暂不可用，请稍后重试（{exc}）"},
        )

    app.include_router(routes.router)

    if FRONTEND_DIST.is_dir():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            target = FRONTEND_DIST / full_path
            if full_path and target.is_file():
                return FileResponse(target)
            return FileResponse(FRONTEND_DIST / "index.html",
                                headers={"Cache-Control": "no-cache"})

    @app.get("/", include_in_schema=False)
    def root():
        if FRONTEND_DIST.is_dir():
            return FileResponse(FRONTEND_DIST / "index.html",
                                headers={"Cache-Control": "no-cache"})
        return {
            "name": "牛来 niulai",
            "docs": "/docs",
            "api": "/api/health",
            "tip": "前端未构建，请先执行 frontend 构建或在浏览器访问 /docs 查看接口文档",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
