"""Bound request buffering before body parsing, including chunked requests.

An exception from receive() can be wrapped by middleware and misreported as a
JSON parse error. Reject oversized bodies before handing them to the parser.
"""

from collections import deque
from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        consumed = 0
        messages = deque()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            consumed += len(message.get("body", b""))
            if consumed > self.max_bytes:
                return await JSONResponse(
                    {"detail": "Request exceeds the 5 MB upload limit."},
                    status_code=413,
                )(scope, receive, send)
            messages.append(message)
            if not message.get("more_body", False):
                break

        async def bounded_receive():
            return messages.popleft() if messages else await receive()

        await self.app(scope, bounded_receive, send)
