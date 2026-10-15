from fastapi import APIRouter

from .routes import events, habits, marks, me, reminders

api_router = APIRouter(prefix="/api")
for module in (me, habits, marks, reminders, events):
    api_router.include_router(module.router)
