"""Domain errors raised by services.

Services don't import FastAPI; main.py maps GameError to an HTTP response, so
business rules stay reusable outside the web layer (CLI, tests, workers).
"""


class GameError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def not_found(what: str) -> GameError:
    return GameError(404, "not_found", f"{what} not found")
