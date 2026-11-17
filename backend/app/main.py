
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging, logger
from app.core.exceptions import register_exception_handlers
from app.api.router import api_router


# Initialize logging
setup_logging()

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "An AI-powered application for "
        "document question answering using RAG."
    ),
    debug=settings.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Register API routes
app.include_router(
    api_router,
    prefix=settings.API_V1_PREFIX
)


@app.get("/")
async def root():

    return {
        "success": True,
        "message": "Welcome to Smart Document Assistant API",
        "docs": "/docs"
    }


@app.on_event("startup")
async def startup_event():

    logger.info(
        "%s started successfully",
        settings.APP_NAME
    )
