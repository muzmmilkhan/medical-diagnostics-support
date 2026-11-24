from fastapi import APIRouter

from app.api.deps import SettingsDep

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
