"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1 import (
    admin, auth, catalog, customers, decision_lab, executive, insights,
    marketing, meta, operations, sql_explorer, exports, forecast,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(meta.router, prefix="/meta", tags=["Reference Data"])
api_router.include_router(executive.router, prefix="/executive", tags=["Executive Dashboard"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customer Analytics"])
api_router.include_router(operations.router, prefix="/operations", tags=["Operations Analytics"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["Catalog & Geography"])
api_router.include_router(marketing.router, prefix="/marketing", tags=["Marketing Analytics"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["Forecasting"])
api_router.include_router(insights.router, prefix="/insights", tags=["AI Insights"])
api_router.include_router(decision_lab.router, prefix="/decision-lab", tags=["Product Decision Lab"])
api_router.include_router(sql_explorer.router, prefix="/sql", tags=["SQL Explorer"])
api_router.include_router(exports.router, prefix="/exports", tags=["Report Exports"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
