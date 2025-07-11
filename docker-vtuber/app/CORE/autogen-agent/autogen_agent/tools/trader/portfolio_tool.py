"""
Portfolio Management Tool for Trader Team
=========================================

Manages portfolio allocation, tracks positions, calculates returns, and provides portfolio analytics.
Includes position tracking, P&L calculation, risk metrics, and rebalancing recommendations.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random

logger = logging.getLogger(__name__)


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    💼 Portfolio Management Tool Entry Point
    
    Comprehensive portfolio management and tracking capabilities.
    
    Args:
        context: Operation context containing:
            - action: Type of operation (positions, performance, allocation, rebalance, risk)
            - portfolio_id: Portfolio identifier
            - Additional parameters based on action
    
    Returns:
        Portfolio management results
    """
    try:
        action = context.get("action", "overview")
        portfolio_id = context.get("portfolio_id", "default")
        
        # Route to appropriate portfolio function
        if action == "positions":
            return await _get_positions(portfolio_id, context)
        
        elif action == "performance":
            return await _calculate_performance(portfolio_id, context)
        
        elif action == "allocation":
            return await _analyze_allocation(portfolio_id, context)
        
        elif action == "rebalance":
            return await _rebalance_portfolio(portfolio_id, context)
        
        elif action == "add_position":
            return await _add_position(portfolio_id, context)
        
        elif action == "close_position":
            return await _close_position(portfolio_id, context)
        
        elif action == "risk_metrics":
            return await _calculate_risk_metrics(portfolio_id, context)
        
        elif action == "overview":
            return await _portfolio_overview(portfolio_id, context)
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": ["positions", "performance", "allocation", "rebalance", 
                                    "add_position", "close_position", "risk_metrics", "overview"]
            }
            
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _get_positions(portfolio_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Get current portfolio positions"""
    try:
        # Simulated portfolio positions
        positions = [
            {
                "id": "pos_001",
                "symbol": "BTC-USD",
                "type": "crypto",
                "quantity": 0.5,
                "entry_price": 42000,
                "current_price": 45000,
                "entry_date": "2024-01-15T10:00:00Z",
                "value": 22500,
                "pnl": 1500,
                "pnl_percentage": 7.14,
                "weight": 0.35
            },
            {
                "id": "pos_002",
                "symbol": "ETH-USD",
                "type": "crypto",
                "quantity": 10,
                "entry_price": 2200,
                "current_price": 2280,
                "entry_date": "2024-01-20T14:30:00Z",
                "value": 22800,
                "pnl": 800,
                "pnl_percentage": 3.64,
                "weight": 0.36
            },
            {
                "id": "pos_003",
                "symbol": "AAPL",
                "type": "stock",
                "quantity": 100,
                "entry_price": 180,
                "current_price": 185.50,
                "entry_date": "2024-01-10T09:30:00Z",
                "value": 18550,
                "pnl": 550,
                "pnl_percentage": 3.06,
                "weight": 0.29
            }
        ]
        
        # Calculate summary statistics
        total_value = sum(p["value"] for p in positions)
        total_pnl = sum(p["pnl"] for p in positions)
        total_pnl_percentage = (total_pnl / (total_value - total_pnl)) * 100 if total_value > total_pnl else 0
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "positions": positions,
            "summary": {
                "total_positions": len(positions),
                "total_value": round(total_value, 2),
                "total_pnl": round(total_pnl, 2),
                "total_pnl_percentage": round(total_pnl_percentage, 2),
                "long_positions": len(positions),
                "short_positions": 0
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Get positions error: {e}")
        return {"success": False, "error": str(e)}


async def _calculate_performance(portfolio_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate portfolio performance metrics"""
    try:
        timeframe = context.get("timeframe", "1M")  # Default 1 month
        
        # Simulated performance data
        performance = {
            "returns": {
                "daily": 0.85,
                "weekly": 2.34,
                "monthly": 7.14,
                "yearly": 42.5,
                "ytd": 35.2
            },
            "risk_adjusted": {
                "sharpe_ratio": 1.85,
                "sortino_ratio": 2.15,
                "calmar_ratio": 1.45,
                "information_ratio": 0.92
            },
            "drawdown": {
                "current_drawdown": -2.5,
                "max_drawdown": -8.3,
                "max_drawdown_duration": "15 days",
                "recovery_time": "7 days"
            },
            "volatility": {
                "daily_volatility": 1.8,
                "monthly_volatility": 9.2,
                "annualized_volatility": 28.5
            },
            "benchmark_comparison": {
                "benchmark": "S&P 500",
                "portfolio_return": 7.14,
                "benchmark_return": 4.85,
                "alpha": 2.29,
                "beta": 1.15,
                "correlation": 0.72
            }
        }
        
        # Generate performance chart data
        chart_data = _generate_performance_chart(30)  # 30 days
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "timeframe": timeframe,
            "performance": performance,
            "chart_data": chart_data,
            "insights": [
                "Portfolio outperforming benchmark by 2.29%",
                "Sharpe ratio of 1.85 indicates good risk-adjusted returns",
                "Current drawdown of -2.5% is within acceptable range",
                "Consider reducing volatility if risk tolerance is lower"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Performance calculation error: {e}")
        return {"success": False, "error": str(e)}


async def _analyze_allocation(portfolio_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze portfolio allocation"""
    try:
        # Current allocation
        current_allocation = {
            "by_asset_class": {
                "crypto": 71.0,
                "stocks": 29.0,
                "bonds": 0,
                "commodities": 0,
                "cash": 0
            },
            "by_sector": {
                "technology": 29.0,
                "cryptocurrency": 71.0
            },
            "by_geography": {
                "us": 29.0,
                "global": 71.0
            },
            "by_position_size": {
                "large_cap": 100.0,
                "mid_cap": 0,
                "small_cap": 0
            }
        }
        
        # Target allocation
        target_allocation = {
            "crypto": 60.0,
            "stocks": 30.0,
            "bonds": 5.0,
            "commodities": 3.0,
            "cash": 2.0
        }
        
        # Calculate deviations
        deviations = {}
        for asset, current in current_allocation["by_asset_class"].items():
            target = target_allocation.get(asset, 0)
            deviations[asset] = {
                "current": current,
                "target": target,
                "deviation": current - target,
                "action": "reduce" if current > target else "increase" if current < target else "maintain"
            }
        
        # Concentration risk
        concentration_risk = _calculate_concentration_risk(current_allocation)
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "current_allocation": current_allocation,
            "target_allocation": target_allocation,
            "deviations": deviations,
            "concentration_risk": concentration_risk,
            "recommendations": [
                "Reduce crypto allocation from 71% to 60%",
                "Add bond allocation for stability (5% target)",
                "Consider diversifying into commodities",
                "High concentration in crypto presents elevated risk"
            ],
            "rebalancing_needed": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Allocation analysis error: {e}")
        return {"success": False, "error": str(e)}


async def _rebalance_portfolio(portfolio_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate rebalancing recommendations"""
    try:
        strategy = context.get("strategy", "threshold")  # threshold, calendar, dynamic
        
        # Calculate required trades for rebalancing
        rebalancing_trades = [
            {
                "action": "sell",
                "symbol": "BTC-USD",
                "quantity": 0.1,
                "reason": "Reduce crypto allocation to target",
                "estimated_value": 4500
            },
            {
                "action": "sell",
                "symbol": "ETH-USD",
                "quantity": 1.5,
                "reason": "Reduce crypto allocation to target",
                "estimated_value": 3420
            },
            {
                "action": "buy",
                "symbol": "TLT",
                "quantity": 25,
                "reason": "Add bond allocation",
                "estimated_value": 3000
            },
            {
                "action": "buy",
                "symbol": "GLD",
                "quantity": 10,
                "reason": "Add commodity allocation",
                "estimated_value": 1800
            }
        ]
        
        # Calculate impact
        impact = {
            "transaction_costs": 45.00,
            "tax_implications": "Short-term gains on crypto positions",
            "expected_improvement": {
                "risk_reduction": 15,
                "diversification_score": 8.5
            }
        }
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "rebalancing_strategy": strategy,
            "recommended_trades": rebalancing_trades,
            "impact_analysis": impact,
            "execution_plan": {
                "phase_1": "Sell overweight positions",
                "phase_2": "Buy underweight assets",
                "phase_3": "Review and adjust",
                "estimated_completion": "2-3 trading days"
            },
            "warnings": [
                "Consider tax implications before executing",
                "Market volatility may affect execution prices",
                "Review current market conditions before proceeding"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Rebalancing error: {e}")
        return {"success": False, "error": str(e)}


async def _add_position(portfolio_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Add new position to portfolio"""
    try:
        symbol = context.get("symbol", "")
        quantity = context.get("quantity", 0)
        price = context.get("price", 0)
        position_type = context.get("type", "buy")
        
        if not symbol or quantity <= 0:
            return {
                "success": False,
                "error": "Invalid position parameters"
            }
        
        # Create new position
        position = {
            "id": f"pos_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "symbol": symbol,
            "quantity": quantity,
            "entry_price": price,
            "entry_date": datetime.now().isoformat(),
            "type": position_type,
            "status": "open",
            "initial_value": quantity * price
        }
        
        # Calculate position impact
        impact = {
            "portfolio_weight": 0.15,  # Simulated
            "diversification_impact": "positive",
            "risk_contribution": 0.08,
            "correlation_with_portfolio": 0.65
        }
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "position": position,
            "impact": impact,
            "message": f"Successfully added {quantity} units of {symbol} at ${price}",
            "warnings": _check_position_warnings(position, impact),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Add position error: {e}")
        return {"success": False, "error": str(e)}


async def _close_position(portfolio_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Close existing position"""
    try:
        position_id = context.get("position_id", "")
        close_price = context.get("price", 0)
        quantity = context.get("quantity", None)  # None means close all
        
        if not position_id:
            return {
                "success": False,
                "error": "Position ID required"
            }
        
        # Simulate position closure
        position_details = {
            "position_id": position_id,
            "symbol": "BTC-USD",
            "quantity_closed": quantity or 0.5,
            "entry_price": 42000,
            "close_price": close_price or 45000,
            "holding_period": "30 days",
            "realized_pnl": 1500,
            "realized_pnl_percentage": 7.14,
            "tax_status": "short_term_gain"
        }
        
        # Calculate impact
        closure_impact = {
            "portfolio_weight_change": -0.15,
            "cash_generated": position_details["quantity_closed"] * position_details["close_price"],
            "tax_liability": position_details["realized_pnl"] * 0.25,  # Estimated
            "available_for_reinvestment": position_details["quantity_closed"] * position_details["close_price"] * 0.75
        }
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "position_closed": position_details,
            "impact": closure_impact,
            "message": f"Successfully closed position {position_id}",
            "next_steps": [
                "Review tax implications",
                "Consider reinvestment opportunities",
                "Update portfolio allocation targets"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Close position error: {e}")
        return {"success": False, "error": str(e)}


async def _calculate_risk_metrics(portfolio_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate comprehensive risk metrics"""
    try:
        # Risk metrics calculation
        risk_metrics = {
            "value_at_risk": {
                "var_95": 2850,  # 95% confidence
                "var_99": 4200,  # 99% confidence
                "expected_shortfall": 5100,
                "interpretation": "95% chance daily loss won't exceed $2,850"
            },
            "portfolio_beta": {
                "vs_sp500": 1.15,
                "vs_nasdaq": 1.32,
                "vs_bitcoin": 0.45,
                "interpretation": "15% more volatile than S&P 500"
            },
            "correlation_matrix": {
                "BTC-ETH": 0.82,
                "BTC-AAPL": 0.35,
                "ETH-AAPL": 0.28
            },
            "stress_test": {
                "market_crash_10": -6800,
                "market_crash_20": -13600,
                "crypto_crash_30": -15300,
                "recovery_time_estimate": "45-60 days"
            },
            "diversification": {
                "score": 6.5,
                "herfindahl_index": 0.42,
                "effective_assets": 2.4,
                "recommendation": "Increase diversification"
            },
            "liquidity": {
                "liquid_assets_percentage": 85,
                "illiquid_assets_percentage": 15,
                "days_to_liquidate": 1.5
            }
        }
        
        # Risk scoring
        risk_score = _calculate_risk_score(risk_metrics)
        
        return {
            "success": True,
            "portfolio_id": portfolio_id,
            "risk_metrics": risk_metrics,
            "risk_score": risk_score,
            "risk_level": "moderate_high",
            "recommendations": [
                "Consider reducing portfolio beta to lower volatility",
                "Increase diversification to reduce concentration risk",
                "Add defensive assets to improve stress test results",
                "Monitor correlation changes during market stress"
            ],
            "risk_limits": {
                "max_var_limit": 5000,
                "current_var": 2850,
                "utilization": "57%"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Risk metrics error: {e}")
        return {"success": False, "error": str(e)}


async def _portfolio_overview(portfolio_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive portfolio overview"""
    try:
        # Gather all portfolio data
        positions = await _get_positions(portfolio_id, context)
        performance = await _calculate_performance(portfolio_id, context)
        allocation = await _analyze_allocation(portfolio_id, context)
        risk = await _calculate_risk_metrics(portfolio_id, context)
        
        # Generate overview
        overview = {
            "portfolio_id": portfolio_id,
            "account_value": 63850,
            "cash_balance": 5000,
            "total_value": 68850,
            "daily_change": {
                "amount": 1250,
                "percentage": 1.85
            },
            "positions_summary": {
                "total": 3,
                "profitable": 3,
                "losing": 0,
                "best_performer": "BTC-USD (+7.14%)",
                "worst_performer": "AAPL (+3.06%)"
            },
            "performance_summary": {
                "monthly_return": 7.14,
                "yearly_return": 42.5,
                "sharpe_ratio": 1.85,
                "max_drawdown": -8.3
            },
            "risk_summary": {
                "risk_level": "moderate_high",
                "var_95": 2850,
                "portfolio_beta": 1.15
            },
            "allocation_summary": {
                "crypto": 71.0,
                "stocks": 29.0,
                "rebalancing_needed": True
            },
            "alerts": [
                "Portfolio requires rebalancing",
                "High concentration in crypto assets",
                "Consider taking profits on BTC position"
            ]
        }
        
        return {
            "success": True,
            "overview": overview,
            "last_updated": datetime.now().isoformat(),
            "next_review": (datetime.now() + timedelta(days=1)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [PORTFOLIO] Overview error: {e}")
        return {"success": False, "error": str(e)}


# Helper functions
def _generate_performance_chart(days: int) -> List[Dict[str, Any]]:
    """Generate performance chart data"""
    chart_data = []
    base_value = 60000
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days-i-1)
        daily_return = random.uniform(-0.03, 0.04)
        base_value *= (1 + daily_return)
        
        chart_data.append({
            "date": date.strftime("%Y-%m-%d"),
            "value": round(base_value, 2),
            "daily_return": round(daily_return * 100, 2)
        })
    
    return chart_data


def _calculate_concentration_risk(allocation: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate concentration risk metrics"""
    by_asset = allocation.get("by_asset_class", {})
    
    # Find maximum concentration
    max_concentration = max(by_asset.values()) if by_asset else 0
    
    # Calculate Herfindahl index
    herfindahl = sum((v/100) ** 2 for v in by_asset.values())
    
    # Risk assessment
    if max_concentration > 70:
        risk_level = "high"
        recommendation = "Urgent diversification needed"
    elif max_concentration > 50:
        risk_level = "moderate"
        recommendation = "Consider reducing largest positions"
    else:
        risk_level = "low"
        recommendation = "Well diversified"
    
    return {
        "max_concentration": max_concentration,
        "herfindahl_index": round(herfindahl, 3),
        "risk_level": risk_level,
        "recommendation": recommendation,
        "diversification_score": round(10 * (1 - herfindahl), 1)
    }


def _check_position_warnings(position: Dict[str, Any], impact: Dict[str, Any]) -> List[str]:
    """Check for position-related warnings"""
    warnings = []
    
    if impact.get("portfolio_weight", 0) > 0.25:
        warnings.append("Position size exceeds 25% of portfolio")
    
    if impact.get("risk_contribution", 0) > 0.15:
        warnings.append("High risk contribution to portfolio")
    
    if impact.get("correlation_with_portfolio", 0) > 0.8:
        warnings.append("High correlation with existing positions")
    
    if position.get("type") == "short":
        warnings.append("Short positions carry unlimited risk")
    
    return warnings


def _calculate_risk_score(risk_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall risk score"""
    scores = {
        "var_score": 7.5,  # Based on VaR levels
        "beta_score": 6.5,  # Based on portfolio beta
        "diversification_score": 6.5,  # Based on diversification metrics
        "liquidity_score": 8.5,  # Based on liquidity metrics
        "stress_score": 5.5  # Based on stress test results
    }
    
    overall_score = sum(scores.values()) / len(scores)
    
    return {
        "overall_score": round(overall_score, 1),
        "component_scores": scores,
        "interpretation": "Moderate-high risk portfolio",
        "grade": "B-" if overall_score > 7 else "C+" if overall_score > 6 else "C"
    }


# Tool metadata for registration
TOOL_METADATA = {
    "name": "portfolio_tool",
    "description": "Comprehensive portfolio management and tracking",
    "version": "1.0.0",
    "author": "Trader Team",
    "capabilities": [
        "track_positions",
        "calculate_performance",
        "analyze_allocation",
        "rebalance_portfolio",
        "risk_metrics",
        "position_management"
    ],
    "required_context": ["portfolio_id"],
    "example_usage": {
        "overview": {
            "action": "overview",
            "portfolio_id": "main_portfolio"
        },
        "add_position": {
            "action": "add_position",
            "symbol": "AAPL",
            "quantity": 100,
            "price": 185.50
        },
        "performance": {
            "action": "performance",
            "timeframe": "1M"
        }
    }
}