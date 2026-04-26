"""FastAPI app factory. Stub — full implementation in Task 14."""

from fastapi import FastAPI


def create_app(*, debug: bool = False) -> FastAPI:
    return FastAPI()


app = create_app(debug=True)
