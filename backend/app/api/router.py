from fastapi import APIRouter

from .routes import habits, marks, me, reminders

api_router = APIRouter(prefix="/api")
for module in (me, habits, marks, reminders):
    api_router.include_router(module.router)
