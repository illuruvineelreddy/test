"""
Main FastAPI Application Entry Point
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from loguru import logger
import sys

from configs.settings import settings
from app.api import routes
from app.websocket import market_data_ws


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level=settings.LOG_LEVEL,
    colorize=True
)
logger.add(
    settings.LOG_FILE,
    rotation="10 MB",
    retention="5 days",
    level=settings.LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Project Astra...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Trading Mode: {settings.TRADING_MODE}")
    logger.info(f"Initial Capital: ₹{settings.INITIAL_CAPITAL:,.2f}")
    
    # Initialize connections (Redis, Database, etc.)
    # TODO: Add initialization logic
    
    yield
    
    # Shutdown
    logger.info("Shutting down Project Astra...")
    # TODO: Add cleanup logic


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-assisted trading infrastructure for Indian markets",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router, prefix=settings.API_PREFIX)

# WebSocket routes will be handled separately


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "trading_mode": settings.TRADING_MODE
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Project Astra",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    logger.info(f"Starting server on {settings.API_HOST}:{settings.API_PORT}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
