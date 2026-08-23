from __future__ import annotations

import logging
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError

from web.database import create_web_engine
from web.models import PriceFilters
from web.repository import PriceRepository
from web.schemas import PricePageResponse
from web.service import PriceService


logger = logging.getLogger(__name__)


def create_app(service: PriceService | None = None) -> FastAPI:
    application = FastAPI(title="SmartShopping Price API", version="1.0.0")
    price_service = service or PriceService(PriceRepository(create_web_engine()))

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
