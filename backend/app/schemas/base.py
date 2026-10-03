from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    """Базовая схема API: поля в JSON — camelCase, как во фронтенде (frontend/src/lib/types.ts)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# Непустая строка без пробелов по краям.
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
