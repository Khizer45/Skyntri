"""
Small outbound HTTP helper (standard library only).

Used for Google sign-in keys, payment providers, image generation and
webhooks. Redirects are never followed, so a response cannot send a request
with credentials to another host.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

MAX_RESPONSE_BYTES = 12 * 1024 * 1024


class HttpError(RuntimeError):
    """The request could not be sent or no response was received."""


@dataclass
class HttpResponse:
    status: int
    body: bytes

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> dict:
        try:
            data = json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise HttpError("The response was not valid JSON") from exc
        return data if isinstance(data, dict) else {"data": data}


class _NoRedirect(urllib_request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401 - urllib hook
        return None


_opener = urllib_request.build_opener(_NoRedirect)


def send(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict | list | None = None,
    form: dict[str, str] | None = None,
    data: bytes | None = None,
    timeout: float = 15.0,
) -> HttpResponse:
    """Send one request. HTTP error statuses are returned, not raised."""
    if not url.lower().startswith(("https://", "http://")):
        raise HttpError("Only http(s) URLs are supported")

    headers = dict(headers or {})
    body = data

    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif form is not None:
        body = urllib_parse.urlencode(form).encode("utf-8")
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    headers.setdefault("User-Agent", "Skyntri/1.0")
    request = urllib_request.Request(url, data=body, headers=headers, method=method.upper())

    try:
        with _opener.open(request, timeout=timeout) as response:  # noqa: S310 - scheme checked above
            return HttpResponse(response.status, response.read(MAX_RESPONSE_BYTES))
    except urllib_error.HTTPError as exc:
        return HttpResponse(exc.code, exc.read(MAX_RESPONSE_BYTES) if exc.fp else b"")
    except (urllib_error.URLError, OSError, ValueError) as exc:
        raise HttpError(f"Request failed: {type(exc).__name__}") from exc
