import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.config import Config
from uvicorn.server import Server

from api.router import router
from config.config import settings
from config.logger import configure_logger


configure_logger()

logger = logging.getLogger(__name__)

app = FastAPI(
    root_path=settings.API_ROOT_PATH,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request_response(request: Request, call_next):
    response = await call_next(request)
    if response.status_code not in [200]:
        logger.info("Request: %s %s - Response: %s", request.method, request.url, response.status_code)
    return response


app.include_router(router)


async def run_fastapi() -> None:
    config = Config(app=app, host="0.0.0.0", port=9000, lifespan="on", log_level="warning")
    server = Server(config)
    await server.serve()


async def main() -> None:
    await asyncio.gather(
        run_fastapi(),
    )


if __name__ == "__main__":
    asyncio.run(main())
