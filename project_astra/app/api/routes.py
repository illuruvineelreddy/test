"""
API Routes - REST endpoints for the trading platform
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime

from configs.settings import settings
from app.risk_engine.risk_manager import risk_engine


router = APIRouter()


@router.get("/risk/summary")
async def get_risk_summary():
    """Get current risk exposure summary"""
    try:
        summary = risk_engine.get_risk_summary()
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/health")
async def check_risk_health():
    """Check if risk engine allows trading"""
    is_healthy = risk_engine.check_health()
    return {
        "success": True,
        "healthy": is_healthy,
        "kill_switch_active": risk_engine.kill_switch_active,
        "reason": risk_engine.kill_switch_reason
    }


@router.post("/risk/kill-switch/activate")
async def activate_kill_switch(reason: str):
    """Manually activate kill switch"""
    risk_engine.activate_kill_switch(reason)
    return {
        "success": True,
        "message": "Kill switch activated",
        "reason": reason
    }


@router.post("/risk/kill-switch/deactivate")
async def deactivate_kill_switch():
    """Manually deactivate kill switch (requires authorization)"""
    risk_engine.deactivate_kill_switch()
    return {
        "success": True,
        "message": "Kill switch deactivated"
    }


@router.get("/positions")
async def get_positions():
    """Get all active positions"""
    try:
        positions = list(risk_engine.active_positions.values())
        return {
            "success": True,
            "count": len(positions),
            "data": positions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capital")
async def get_capital_info():
    """Get capital and PnL information"""
    summary = risk_engine.get_risk_summary()
    return {
        "success": True,
        "data": {
            "initial_capital": summary['initial_capital'],
            "current_capital": summary['current_capital'],
            "total_pnl": summary['total_pnl'],
            "total_pnl_pct": (summary['total_pnl'] / summary['initial_capital']) * 100,
            "daily_pnl": summary['daily_pnl'],
            "daily_pnl_pct": summary['daily_pnl_pct']
        }
    }


@router.get("/strategies")
async def get_strategies():
    """Get list of available strategies"""
    from app.strategies.strategy_engine import get_all_strategies
    
    strategies = get_all_strategies()
    enabled = settings.ENABLED_STRATEGIES
    
    return {
        "success": True,
        "data": {
            "all_strategies": strategies,
            "enabled_strategies": enabled
        }
    }


@router.get("/settings")
async def get_settings():
    """Get current application settings (sanitized)"""
    return {
        "success": True,
        "data": {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "trading_mode": settings.TRADING_MODE,
            "initial_capital": settings.INITIAL_CAPITAL,
            "risk_per_trade_pct": settings.RISK_PER_TRADE_PCT,
            "daily_loss_limit_pct": settings.DAILY_LOSS_LIMIT_PCT,
            "max_positions": settings.MAX_POSITIONS,
            "max_leverage": settings.MAX_LEVERAGE,
            "ml_confidence_threshold": settings.ML_CONFIDENCE_THRESHOLD,
            "enabled_strategies": settings.ENABLED_STRATEGIES
        }
    }
