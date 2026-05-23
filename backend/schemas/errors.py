"""Unified error response schema for all router HTTPException sites."""

from fastapi import HTTPException
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: dict | None = None


def http_error(status_code: int, code: str, message: str, **kwargs) -> HTTPException:
    """Build an HTTPException whose detail is already in the ErrorResponse shape.

    Usage::

        raise http_error(404, "crop_not_found", "Crop not found")
        raise http_error(503, "model_unavailable", "Crop model not loaded",
                         hint="restart the server")

    The ``**kwargs`` are stored under the ``detail`` key of the payload and
    must be JSON-serializable.
    """
    payload: dict = {"code": code, "message": message}
    if kwargs:
        payload["detail"] = kwargs
    return HTTPException(status_code=status_code, detail=payload)
