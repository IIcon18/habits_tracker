import os

# До импорта приложения: тестовая база и токен бота.
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+asyncpg://kaplya:kaplya@localhost:5433/kaplya_test"
)
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["BOT_TOKEN"] = "123456:TEST-token"
os.environ["DEBUG"] = "0"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402

from .initdata import make_init_data  # noqa: E402

HERE = os.path.dirname(__file__)


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    """Схема создаётся настоящей миграцией — заодно проверяем её."""
    cfg = Config(os.path.join(HERE, "..", "alembic.ini"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
async def clean_tables():
    yield
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, habits, habit_pauses, marks, reminders CASCADE"))


def client_for(user_id: int, timezone: str = "Europe/Moscow") -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"tma {make_init_data(user_id)}", "X-Timezone": timezone},
    )


@pytest.fixture
async def client():
    async with client_for(1001) as c:
        yield c
