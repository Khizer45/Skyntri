from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import IngredientScan, ProgressCheck, Report, SkinAnalysis, User
from app.dependencies import get_current_user
from app.schemas import HistoryItemOut, HistoryResponse

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryResponse)
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = (
        db.query(SkinAnalysis)
        .filter(SkinAnalysis.user_id == current_user.id)
        .order_by(desc(SkinAnalysis.created_at))
        .all()
    )
    scans = (
        db.query(IngredientScan)
        .filter(IngredientScan.user_id == current_user.id)
        .order_by(desc(IngredientScan.created_at))
        .all()
    )
    progress = (
        db.query(ProgressCheck)
        .filter(ProgressCheck.user_id == current_user.id)
        .order_by(desc(ProgressCheck.created_at))
        .all()
    )
    reports = db.query(Report).filter(Report.user_id == current_user.id).order_by(desc(Report.created_at)).all()

    return HistoryResponse(
        analyses=[
            HistoryItemOut(
                id=a.id,
                type="Skin Analysis",
                result=a.predicted_condition,
                confidence=a.confidence_score,
                date=a.created_at,
                status="Reviewed",
            )
            for a in analyses
        ],
        scans=[
            HistoryItemOut(
                id=s.id,
                type="Ingredient Scan",
                result=s.product_name or f"{s.total_ingredients} ingredients scanned",
                confidence=None,
                date=s.created_at,
                status="Completed",
            )
            for s in scans
        ],
        progress=[
            HistoryItemOut(
                id=p.id,
                type="Progress Check",
                result=f"{p.status} · {p.score:.0f}%",
                confidence=None,
                date=p.created_at,
                status="Completed",
            )
            for p in progress
        ],
        reports=[
            HistoryItemOut(
                id=r.id,
                type="Report",
                result=r.title,
                confidence=None,
                date=r.created_at,
                status="Generated",
            )
            for r in reports
        ],
    )
