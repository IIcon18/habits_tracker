"""Ошибки бизнес-логики. Сервисы не знают про HTTP: в ответы их переводит app/main.py,
а бот (следующая итерация) — в тексты сообщений."""


class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFound(DomainError):
    pass


class Conflict(DomainError):
    pass


class InvalidInput(DomainError):
    pass
