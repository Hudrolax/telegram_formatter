from fastapi import APIRouter


router = APIRouter(prefix="/healthcheck", tags=["service"])


@router.get("")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
