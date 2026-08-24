from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from web.database import create_web_engine
from web.health import database_is_ready
from web.models import PriceFilters, PricePage
from web.repository import PriceRepository
from web.schemas import PricePageResponse
from web.service import PriceService


logger = logging.getLogger(__name__)
WEB_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


def create_app(
    service: PriceService | None = None,
    health_engine: Engine | None = None,
) -> FastAPI:
    application = FastAPI(title="SmartShopping Price API", version="1.0.0")
    application.mount(
        "/static",
        StaticFiles(directory=str(WEB_DIR / "static")),
        name="static",
    )
    if service is None:
        readiness_engine = health_engine or create_web_engine()
        price_service = PriceService(PriceRepository(readiness_engine))
    else:
        price_service = service
        service_repository = getattr(service, "repository", None)
        service_engine = getattr(service_repository, "engine", None)
        readiness_engine = health_engine or service_engine or create_web_engine()

    @application.get("/health")
    async def health():
        try:
            if database_is_ready(readiness_engine):
                return {"status": "ok", "database": "ready"}
            logger.error("Database health check found no price snapshots")
        except SQLAlchemyError:
            logger.exception("Database health check failed")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "database": "unavailable",
            },
        )

    @application.get("/", response_class=HTMLResponse, name="price_page")
    async def price_page(
        request: Request,
        q: str | None = Query(default=None, max_length=100),
        market_type: Literal["retail", "wholesale"] | None = None,
        page: int = Query(default=1, ge=1),
    ) -> HTMLResponse:
        filters = PriceFilters(
            query=q,
            market_type=market_type,
            page=page,
            page_size=20,
        )
        error: str | None = None
        status_code = 200
        try:
            result = price_service.search(filters)
        except SQLAlchemyError:
            logger.exception("Price page query failed")
            result = PricePage((), page, 20, 0, 0)
            error = "가격 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
            status_code = 503

        query_values = {"q": q or "", "market_type": market_type or ""}
        previous_url = (
            str(request.url.include_query_params(page=page - 1, **query_values))
            if page > 1
            else None
        )
        next_url = (
            str(request.url.include_query_params(page=page + 1, **query_values))
            if page < result.total_pages
            else None
        )
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "result": result,
                "q": q or "",
                "market_type": market_type or "",
                "error": error,
                "previous_url": previous_url,
                "next_url": next_url,
            },
            status_code=status_code,
        )

    @application.get("/api/prices", response_model=PricePageResponse)
    async def list_prices(
        q: str | None = Query(default=None, max_length=100),
        market_type: Literal["retail", "wholesale"] | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=20, ge=1, le=100),
    ) -> PricePageResponse:
        filters = PriceFilters(
            query=q,
            market_type=market_type,
            page=page,
            page_size=page_size,
        )
        try:
            result = price_service.search(filters)
        except SQLAlchemyError as exc:
            logger.exception("Price query failed")
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "PRICE_SERVICE_UNAVAILABLE",
                    "message": "가격 정보를 불러올 수 없습니다.",
                },
            ) from exc
        return PricePageResponse.model_validate(result)

    return application


app = create_app()
