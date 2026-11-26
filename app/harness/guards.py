from pydantic_ai_harness.guardrails.detectors import for_text,personal_data,secret_data

_SECRET=secret_data(
    extra={"password": r"(?i)\b(?:password|passcode|pin|otp)\s*(?:is|:|=)\s*\S+"}
)

_PII=personal_data(
    only=["credit_card"],
    extra={
        "aadhaar": r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b",
        "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    },
)

REDACT=[for_text(_SECRET),for_text(_PII)]