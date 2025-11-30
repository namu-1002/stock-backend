# app/report/report_router.py
from fastapi import APIRouter
from app.schemas.report_schema import ReportRequest
from app.services.report_service import generate_report

router = APIRouter(
    prefix="/api/stocks",
    tags=["Stock Reports"]
)

@router.post("/report")
def get_report(request: ReportRequest):
    return generate_report(request.ticker)
