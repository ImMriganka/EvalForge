from fastapi import APIRouter
from app.schemas import InjectionRunRequest, InjectionOut

router = APIRouter()


@router.post("/run", response_model=InjectionOut, summary="Run prompt injection test suite")
def run_injection(req: InjectionRunRequest):
    """
    Phase 4 will implement the 6-category injection attack suite.
    Returns a stub for now.
    """
    stub_summary = {
        "total": 0,
        "injected": 0,
        "injection_rate": 0.0,
        "robustness": 1.0,
        "status": "not implemented — Phase 4",
    }
    return InjectionOut(summary=stub_summary, details={})
