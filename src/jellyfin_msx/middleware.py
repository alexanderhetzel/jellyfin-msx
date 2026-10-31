from starlette.responses import JSONResponse


class PairBodyLimit:
    """Bound actual bytes before form parsing, including chunked requests."""

    def __init__(self, app, maximum=8192):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"]
            not in {
                "/pair",
                "/api/device-authorization/enroll",
                "/api/device-authorization/renew",
                "/api/playback/start",
                "/api/playback/options",
                "/api/playback/observations",
            }
        ):
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > self.maximum:
                response = JSONResponse({"error": "Request body is too large."}, status_code=413)
                return await response(scope, receive, send)
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        delivered = False

        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, bounded_receive, send)
