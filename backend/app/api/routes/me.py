from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas import MeOut
from app.services.users import user_today

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut)
async def me(user: CurrentUser) -> MeOut:
    return MeOut(id=user.id, first_name=user.first_name, timezone=user.timezone, today=user_today(user))
