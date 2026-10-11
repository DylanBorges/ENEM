from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.exams import router as exams_router
from app.api.v1.attempts import router as attempts_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.essays import router as essays_router
from app.api.v1.reports import router as reports_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.institutions import router as institutions_router
from app.api.v1.admin import router as admin_router
from app.api.v1.jobs import router as jobs_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(exams_router)
api_router.include_router(attempts_router)
api_router.include_router(scoring_router)
api_router.include_router(essays_router)
api_router.include_router(reports_router)
api_router.include_router(dashboard_router)
api_router.include_router(institutions_router)
api_router.include_router(admin_router)
api_router.include_router(jobs_router)
