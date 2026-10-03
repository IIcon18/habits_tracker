import time

import pytest

from app.core.security import InvalidInitData, validate_init_data

from .initdata import BOT_TOKEN, make_init_data

DAY = 24 * 60 * 60


def test_valid_init_data():
    user = validate_init_data(make_init_data(42, username="ilya"), BOT_TOKEN, DAY)
    assert user.id == 42
    assert user.first_name == "Илья"
    assert user.username == "ilya"


def test_tampered_hash():
    data = make_init_data(42).replace("%22id%22%3A42", "%22id%22%3A43")
    with pytest.raises(InvalidInitData, match="подпись"):
        validate_init_data(data, BOT_TOKEN, DAY)


def test_other_bot_token():
    with pytest.raises(InvalidInitData, match="подпись"):
        validate_init_data(make_init_data(42, bot_token="999:other"), BOT_TOKEN, DAY)


def test_expired():
    old = int(time.time()) - DAY - 60
    with pytest.raises(InvalidInitData, match="просрочена"):
        validate_init_data(make_init_data(42, auth_date=old), BOT_TOKEN, DAY)


def test_missing_hash():
    with pytest.raises(InvalidInitData, match="hash"):
        validate_init_data("auth_date=1&user=%7B%7D", BOT_TOKEN, DAY)
