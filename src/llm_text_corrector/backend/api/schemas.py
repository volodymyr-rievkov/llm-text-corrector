"""HTTP request and response shapes."""

from typing import Literal

from pydantic import BaseModel


class CorrectionBody(BaseModel):
    text: str


class CorrectionResponse(BaseModel):
    corrected_text: str


class ErrorResponse(BaseModel):
    code: str
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
