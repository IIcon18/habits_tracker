from fastapi import APIRouter

from ..auth import CurrentUser
from ..deps import user_today
from ..schemas import MeOut

router = APIRouter()


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser) -> MeOut:
    return MeOut(id=user.id, first_name=user.first_name, timezone=user.timezone, today=user_today(user))
