from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.daily_review import DailyReviewResponse
from app.services.daily_review_service import daily_review_service

router = APIRouter(prefix='/api/daily-review', tags=['daily-review'])


@router.get('', response_model=DailyReviewResponse)
def get_daily_review(db: Session = Depends(get_db)) -> DailyReviewResponse:
    return daily_review_service.get_daily_review(db)
