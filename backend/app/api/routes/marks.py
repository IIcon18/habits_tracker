import datetime as dt
import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.models import Mark
from app.schemas import MarkIn, MarkOut
from app.services import marks

router = APIRouter(prefix="/habits/{habit_id}/marks", tags=["marks"])


@router.put("/{day}", response_model=MarkOut)
async def put_mark(habit_id: uuid.UUID, day: dt.date, body: MarkIn, user: CurrentUser, session: SessionDep) -> Mark:
    return await marks.put_mark(session, user, habit_id, day, body.kind, body.at)


@router.delete("/{day}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mark(habit_id: uuid.UUID, day: dt.date, user: CurrentUser, session: SessionDep) -> Response:
    await marks.delete_mark(session, user, habit_id, day)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
