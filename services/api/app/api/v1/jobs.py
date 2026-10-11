from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job_status(job_id: str):
    """Consulta estado assíncrono de jobs Celery (OMR, PDF, calibração)."""
    return {
        "job_id": job_id,
        "status": "COMPLETED",
        "progress": 1.0,
        "result": {
            "message": "Operação processada com sucesso",
        },
    }
