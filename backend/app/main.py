import asyncio
import hashlib
import hmac
import logging
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.ml.classifier import load_classifier
from app.api.routes import router
from app.core.body_limit import BodyLimitMiddleware

logger = logging.getLogger("verifact")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migrations are explicit. Model startup runs outside the event loop.
    try:
        app.state.classifier = await asyncio.to_thread(load_classifier)
    except Exception:
        logger.error("Model artifact could not be loaded; language-only mode enabled.")
        app.state.classifier = None
    from app.services.nlp import pipeline

    await asyncio.to_thread(pipeline)
    yield


app = FastAPI(title="VeriFact AI", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)
# Generated secret survives reloads without entering source control.
if not settings.session_secret:
    from pathlib import Path

    secret_path = Path(__file__).resolve().parents[1] / ".session-secret"
    try:
        with secret_path.open("x") as secret_file:
            secret_file.write(secrets.token_hex(32))
        secret_path.chmod(0o600)
    except FileExistsError:
        pass
    settings.session_secret = secret_path.read_text().strip()

buckets = defaultdict(deque)


def sign(value: str) -> str:
    return hmac.new(
        settings.session_secret.encode(), value.encode(), hashlib.sha256
    ).hexdigest()


@app.middleware("http")
async def session_and_limits(request: Request, call_next):
    cookie = request.cookies.get("verifact_session", "")
    value, _, signature = cookie.partition(".")
    valid = len(value) == 48 and hmac.compare_digest(sign(value), signature)
    session_id = value if valid else secrets.token_hex(24)
    request.state.session_id = session_id
    if request.method in {"POST", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin != settings.frontend_origin:
            return JSONResponse(
                {"detail": "This request origin is not allowed."}, status_code=403
            )
        # Key by client IP as well as session: clearing cookies does not bypass the local limiter.
        address = request.client.host if request.client else "unknown"
        now = time.monotonic()
        for key in (f"ip:{address}", f"session:{session_id}"):
            bucket = buckets[key]
            while bucket and bucket[0] < now - 60:
                bucket.popleft()
            if len(bucket) >= 30:
                return JSONResponse(
                    {"detail": "Too many requests. Please wait a minute and retry."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            bucket.append(now)
        if len(buckets) > 10000:
            for key in list(buckets):
                if not buckets[key] or buckets[key][-1] < now - 60:
                    del buckets[key]
        try:
            if (
                int(request.headers.get("content-length", "0"))
                > settings.max_upload_bytes + 65536
            ):
                return JSONResponse(
                    {"detail": "Request exceeds the 5 MB upload limit."},
                    status_code=413,
                )
        except ValueError:
            return JSONResponse({"detail": "Invalid content length."}, status_code=400)
    response = await call_next(request)
    if not valid:
        response.set_cookie(
            "verifact_session",
            f"{session_id}.{sign(session_id)}",
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    messages = [str(e["msg"]).removeprefix("Value error, ") for e in exc.errors()]
    return JSONResponse({"detail": " ".join(messages)}, status_code=422)


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    logger.error("Database operation failed.")
    return JSONResponse(
        {
            "detail": "History storage is unavailable. Check the database connection and run migrations before retrying."
        },
        status_code=503,
    )


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logger.error("Request failed: %s", type(exc).__name__)
    return JSONResponse(
        {
            "detail": "The analysis could not be completed. Please retry or contact the administrator."
        },
        status_code=500,
    )


app.include_router(router)
app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_upload_bytes + 65536)
