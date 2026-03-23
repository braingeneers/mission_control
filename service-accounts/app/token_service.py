from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from flask import Flask, jsonify, request


app = Flask(__name__)


AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET")
if not AUTH0_CLIENT_ID or not AUTH0_CLIENT_SECRET:
    raise ValueError(
        "AUTH0_CLIENT_ID and AUTH0_CLIENT_SECRET must be set in environment variables."
    )

AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "dev-jkxyxuthob0qc1nw.us.auth0.com")
AUTH0_API_AUDIENCE = os.environ.get(
    "AUTH0_API_AUDIENCE", "https://auth.braingeneers.gi.ucsc.edu/"
)

DEFAULT_SERVICE_ACCOUNT_EXPIRATION_DAYS = int(
    os.environ.get("DEFAULT_EXPIRATION_DAYS", "120")
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _parse_requested_days() -> int:
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        return int(body.get("days", DEFAULT_SERVICE_ACCOUNT_EXPIRATION_DAYS))
    return int(
        request.args.get("days", DEFAULT_SERVICE_ACCOUNT_EXPIRATION_DAYS, type=int)
    )


def _json_response(
    payload: dict[str, Any], *, status: int = 200, cacheable: bool = False
):
    response = jsonify(payload)
    response.status_code = status
    if cacheable:
        response.headers["Cache-Control"] = "public, max-age=300"
    else:
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    return response


def _service_account_token(days: int) -> dict[str, Any]:
    expires_at = _utcnow() + timedelta(days=days)
    token_payload = {
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": AUTH0_API_AUDIENCE,
        "grant_type": "client_credentials",
    }
    token_response = requests.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",
        json=token_payload,
        timeout=30,
    )
    if token_response.status_code != 200:
        raise RuntimeError(token_response.text)

    token_data = token_response.json()
    return {
        "access_token": token_data["access_token"],
        "expires_at": _format_utc(expires_at),
    }


@app.route("/generate_token", methods=["GET", "POST"])
def generate_token():
    try:
        token_data = _service_account_token(_parse_requested_days())
    except Exception as exc:  # pragma: no cover - runtime error path
        return _json_response(
            {"error": "Failed to generate token", "details": str(exc)},
            status=500,
        )
    return _json_response(token_data)


@app.route("/healthz", methods=["GET"])
def healthz():
    return _json_response(
        {
            "status": "ok",
            "service_account_audience": AUTH0_API_AUDIENCE,
            "issuer": f"https://{AUTH0_DOMAIN}/",
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
