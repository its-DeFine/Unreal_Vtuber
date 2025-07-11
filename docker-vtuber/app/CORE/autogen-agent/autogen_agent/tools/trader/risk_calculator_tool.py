"""
Risk Calculator Tool for Trader Team
====================================

Calculates position sizing, risk assessment, stop-loss levels, and portfolio risk metrics.
Includes Kelly Criterion, position sizing algorithms, and risk/reward calculations.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import math
import random

logger = logging.getLogger(__name__)


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    ⚠️ Risk Calculator Tool Entry Point
    
    Comprehensive risk assessment and position sizing calculations.
    
    Args:
        context: Operation context containing:
            - action: Type of calculation (position_size, stop_loss, risk_reward, kelly, portfolio_risk)
            - Additional parameters based on action
    
    Returns:
        Risk calculation results
    """
    try:
        action = context.get("action", "position_size")
        
        # Route to appropriate risk calculation
        if action == "position_size":
            return await _calculate_position_size(context)
        
        elif action == "stop_loss":
            return await _calculate_stop_loss(context)
        
        elif action == "risk_reward":
            return await _analyze_risk_reward(context)
        
        elif action == "kelly":
            return await _kelly_criterion(context)
        
        elif action == "portfolio_risk":
            return await _portfolio_risk_analysis(context)
        
        elif action == "monte_carlo":
            return await _monte_carlo_simulation(context)
        
        elif action == "optimal_f":
            return await _optimal_f_calculation(context)
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": ["position_size", "stop_loss", "risk_reward", 
                                    "kelly", "portfolio_risk", "monte_carlo", "optimal_f"]
            }
            
    except Exception as e:
        logger.error(f"❌ [RISK_CALCULATOR] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _calculate_position_size(context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate optimal position size based on risk parameters"""
    try:
        account_balance = context.get("account_balance", 100000)
        risk_percentage = context.get("risk_percentage", 1.0)  # % of account to risk
        entry_price = context.get("entry_price", 45000)
        stop_loss_price = context.get("stop_loss_price", 43500)
        
        # Validate inputs
        if stop_loss_price >= entry_price:
            return {
                "success": False,
                "error": "Stop loss must be below entry price for long positions"
            }
        
        # Calculate risk per share/unit
        risk_per_unit = entry_price - stop_loss_price
        
        # Calculate position risk amount
        risk_amount = account_balance * (risk_percentage / 100)
        
        # Calculate position size
        position_size = risk_amount / risk_per_unit
        
        # Calculate position value
        position_value = position_size * entry_price
        
        # Position as percentage of account
        position_percentage = (position_value / account_balance) * 100
        
        # Additional position sizing methods
        alternative_methods = {
            "fixed_ratio": _fixed_ratio_position_size(account_balance, risk_amount),
            "volatility_based": _volatility_based_position_size(account_balance, entry_price),
            "atr_based": _atr_based_position_size(account_balance, entry_price, risk_percentage)
        }
        
        return {
            "success": True,
            "position_sizing": {
                "recommended_size": round(position_size, 4),
                "position_value": round(position_value, 2),
                "position_percentage": round(position_percentage, 2),
                "risk_amount": round(risk_amount, 2),
                "risk_per_unit": round(risk_per_unit, 2)
            },
            "alternative_methods": alternative_methods,
            "risk_metrics": {
                "max_loss": round(risk_amount, 2),
                "risk_reward_ratio": _calculate_risk_reward_ratio(entry_price, stop_loss_price, entry_price * 1.05),
                "breakeven_win_rate": round(100 / (1 + _calculate_risk_reward_ratio(entry_price, stop_loss_price, entry_price * 1.05)), 2)
            },
            "warnings": _check_position_size_warnings(position_percentage, risk_percentage),
            "recommendations": [
                f"Position size: {round(position_size, 4)} units",
                f"Maximum risk: ${round(risk_amount, 2)}",
                f"Position will be {round(position_percentage, 1)}% of account"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [RISK_CALCULATOR] Position size error: {e}")
        return {"success": False, "error": str(e)}


async def _calculate_stop_loss(context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate optimal stop loss levels"""
    try:
        entry_price = context.get("entry_price", 45000)
        method = context.get("method", "atr")  # atr, percentage, support, volatility
        timeframe = context.get("timeframe", "1d")
        
        stop_losses = {}
        
        # ATR-based stop loss
        atr = entry_price * 0.02  # Simulated 2% ATR
        stop_losses["atr_based"] = {
            "1x_atr": round(entry_price - atr, 2),
            "1.5x_atr": round(entry_price - (atr * 1.5), 2),
            "2x_atr": round(entry_price - (atr * 2), 2),
            "recommended": round(entry_price - (atr * 1.5), 2)
        }
        
        # Percentage-based stop loss
        stop_losses["percentage_based"] = {
            "conservative_2%": round(entry_price * 0.98, 2),
            "moderate_3%": round(entry_price * 0.97, 2),
            "aggressive_5%": round(entry_price * 0.95, 2),
            "recommended": round(entry_price * 0.97, 2)
        }
        
        # Support level based
        support_levels = [44500, 44000, 43200]  # Simulated support levels
        stop_losses["support_based"] = {
            "below_first_support": support_levels[0] - 50,
            "below_second_support": support_levels[1] - 50,
            "major_support": support_levels[2] - 50,
            "recommended": support_levels[0] - 50
        }
        
        # Volatility-based stop loss
        volatility = 0.025  # 2.5% daily volatility
        stop_losses["volatility_based"] = {
            "1_std_dev": round(entry_price * (1 - volatility), 2),
            "1.5_std_dev": round(entry_price * (1 - volatility * 1.5), 2),
            "2_std_dev": round(entry_price * (1 - volatility * 2), 2),
            "recommended": round(entry_price * (1 - volatility * 1.5), 2)
        }
        
        # Trailing stop recommendations
        trailing_stops = {
            "percentage_trailing": 3.0,
            "atr_trailing": 1.5,
            "chandelier_exit": round(entry_price - (atr * 3), 2),
            "parabolic_sar": round(entry_price * 0.975, 2)
        }
        
        # Select primary recommendation based on method
        primary_stop = stop_losses[f"{method}_based"]["recommended"]
        
        return {
            "success": True,
            "entry_price": entry_price,
            "stop_loss_levels": stop_losses,
            "trailing_stops": trailing_stops,
            "primary_recommendation": {
                "method": method,
                "stop_loss": primary_stop,
                "distance": round(entry_price - primary_stop, 2),
                "risk_percentage": round(((entry_price - primary_stop) / entry_price) * 100, 2)
            },
            "risk_analysis": {
                "probability_of_hit": _calculate_stop_hit_probability(entry_price, primary_stop, volatility),
                "expected_holding_period": f"{_estimate_holding_period(volatility)} days",
                "risk_adjusted_return": _calculate_risk_adjusted_return(entry_price, primary_stop)
            },
            "recommendations": [
                f"Primary stop loss at ${primary_stop}",
                f"Consider trailing stop after {round(entry_price * 1.02, 2)}",
                "Adjust stop based on market volatility changes"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [RISK_CALCULATOR] Stop loss calculation error: {e}")
        return {"success": False, "error": str(e)}


async def _analyze_risk_reward(context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze risk/reward ratios and trade viability"""
    try:
        entry_price = context.get("entry_price", 45000)
        stop_loss = context.get("stop_loss", 43500)
        take_profits = context.get("take_profits", [46500, 48000, 50000])
        win_rate = context.get("win_rate", 0.45)  # Historical win rate
        
        # Calculate risk
        risk = entry_price - stop_loss
        risk_percentage = (risk / entry_price) * 100
        
        # Analyze each take profit level
        rr_analysis = []
        for tp in take_profits:
            reward = tp - entry_price
            rr_ratio = reward / risk
            
            # Calculate expected value
            expected_value = (win_rate * reward) - ((1 - win_rate) * risk)
            ev_percentage = (expected_value / entry_price) * 100
            
            # Calculate required win rate for breakeven
            required_win_rate = 1 / (1 + rr_ratio)
            
            rr_analysis.append({
                "take_profit": tp,
                "reward": round(reward, 2),
                "risk_reward_ratio": round(rr_ratio, 2),
                "expected_value": round(expected_value, 2),
                "ev_percentage": round(ev_percentage, 2),
                "required_win_rate": round(required_win_rate * 100, 2),
                "edge": round((win_rate - required_win_rate) * 100, 2)
            })
        
        # Overall trade assessment
        avg_rr = sum(item["risk_reward_ratio"] for item in rr_analysis) / len(rr_analysis)
        avg_ev = sum(item["expected_value"] for item in rr_analysis) / len(rr_analysis)
        
        trade_quality = _assess_trade_quality(avg_rr, win_rate, avg_ev)
        
        # Kelly criterion for this trade
        kelly_percentage = _calculate_kelly_percentage(win_rate, avg_rr)
        
        return {
            "success": True,
            "trade_setup": {
                "entry": entry_price,
                "stop_loss": stop_loss,
                "risk": round(risk, 2),
                "risk_percentage": round(risk_percentage, 2)
            },
            "risk_reward_analysis": rr_analysis,
            "trade_metrics": {
                "average_rr_ratio": round(avg_rr, 2),
                "average_expected_value": round(avg_ev, 2),
                "win_rate_assumption": round(win_rate * 100, 2),
                "kelly_percentage": round(kelly_percentage, 2),
                "trade_quality": trade_quality
            },
            "recommendations": _generate_rr_recommendations(avg_rr, win_rate, trade_quality),
            "position_sizing": {
                "conservative": "0.5% - 1% of account",
                "moderate": "1% - 2% of account",
                "aggressive": f"{round(kelly_percentage / 2, 1)}% of account (Half Kelly)",
                "kelly_optimal": f"{round(kelly_percentage, 1)}% of account"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ [RISK_CALCULATOR] Risk/reward analysis error: {e}")
        return {"success": False, "error": str(e)}


async def _kelly_criterion(context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate Kelly Criterion for optimal position sizing"""
    try:
        win_probability = context.get("win_probability", 0.55)
        win_amount = context.get("win_amount", 1.5)  # Average win as multiple of loss
        loss_amount = context.get("loss_amount", 1.0)  # Normalized to 1
        current_bankroll = context.get("bankroll", 100000)
        
        # Basic Kelly formula: f = (p*b - q) / b
        # where f = fraction to bet, p = win probability, q = loss probability, b = odds
        q = 1 - win_probability
        b = win_amount / loss_amount
        
        kelly_fraction = (win_probability * b - q) / b
        
        # Calculate variations
        half_kelly = kelly_fraction / 2
        quarter_kelly = kelly_fraction / 4
        
        # Risk of ruin calculations
        ror_full_kelly = _calculate_risk_of_ruin(kelly_fraction, win_probability, 0.1)
        ror_half_kelly = _calculate_risk_of_ruin(half_kelly, win_probability, 0.1)
        
        # Growth rate calculations
        growth_rate_full = _calculate_growth_rate(kelly_fraction, win_probability, b)
        growth_rate_half = _calculate_growth_rate(half_kelly, win_probability, b)
        
        # Position size recommendations
        position_sizes = {
            "full_kelly": round(current_bankroll * kelly_fraction, 2),
            "half_kelly": round(current_bankroll * half_kelly, 2),
            "quarter_kelly": round(current_bankroll * quarter_kelly, 2)
        }
        
        # Simulate outcomes
        simulations = _simulate_kelly_outcomes(current_bankroll, kelly_fraction, win_probability, b, 100)
        
        return {
            "success": True,
            "kelly_calculation": {
                "win_probability": round(win_probability * 100, 2),
                "loss_probability": round(q * 100, 2),
                "payoff_ratio": round(b, 2),
                "kelly_fraction": round(kelly_fraction * 100, 2),
                "half_kelly": round(half_kelly * 100, 2),
                "quarter_kelly": round(quarter_kelly * 100, 2)
            },
            "position_sizes": position_sizes,
            "risk_metrics": {
                "risk_of_ruin_full": round(ror_full_kelly * 100, 2),
                "risk_of_ruin_half": round(ror_half_kelly * 100, 2),
                "expected_growth_full": round(growth_rate_full * 100, 2),
                "expected_growth_half": round(growth_rate_half * 100, 2)
            },
            "simulation_results": simulations,
            "recommendations": [
                f"Optimal Kelly: {round(kelly_fraction * 100, 2)}% of bankroll",
                f"Conservative (Half Kelly): {round(half_kelly * 100, 2)}% of bankroll",
                "Consider market conditions and correlation when sizing",
                "Never exceed full Kelly allocation"
            ],
            "warnings": _check_kelly_warnings(kelly_fraction, win_probability)
        }
        
    except Exception as e:
        logger.error(f"❌ [RISK_CALCULATOR] Kelly criterion error: {e}")
        return {"success": False, "error": str(e)}


async def _portfolio_risk_analysis(context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze overall portfolio risk"""
    try:
        positions = context.get("positions", [])
        total_capital = context.get("total_capital", 100000)
        
        # Calculate individual position risks
        position_risks = []
        total_risk = 0
        
        for pos in positions:
            pos_value = pos.get("value", 0)
            pos_volatility = pos.get("volatility", 0.02)
            pos_beta = pos.get("beta", 1.0)
            
            # Position risk
            pos_risk = pos_value * pos_volatility
            total_risk += pos_risk
            
            position_risks.append({
                "symbol": pos.get("symbol", "Unknown"),
                "value": pos_value,
                "risk_contribution": round(pos_risk, 2),
                "risk_percentage": round((pos_risk / total_capital) * 100, 2),
                "volatility": round(pos_volatility * 100, 2),
                "beta": pos_beta
            })
        
        # Portfolio-level metrics
        portfolio_volatility = total_risk / total_capital
        sharpe_ratio = _calculate_sharpe_ratio(0.08, portfolio_volatility, 0.02)  # 8% return, 2% risk-free
        
        # Correlation matrix (simplified)
        correlation_impact = 0.7  # Average correlation
        diversified_risk = total_risk * math.sqrt(correlation_impact)
        
        # Value at Risk (VaR)
        var_95 = _calculate_var(total_capital, portfolio_volatility, 0.95)
        var_99 = _calculate_var(total_capital, portfolio_volatility, 0.99)
        
        # Stress testing
        stress_scenarios = {
            "market_crash": -0.20,
            "sector_shock": -0.15,
            "black_swan": -0.35
        }
        
        stress_results = {}
        for scenario, shock in stress_scenarios.items():
            loss = total_capital * shock * (1 + portfolio_volatility)
            stress_results[scenario] = round(loss, 2)
        
        return {
            "success": True,
            "portfolio_summary": {
                "total_capital": total_capital,
                "positions_count": len(positions),
                "total_risk_exposure": round(total_risk, 2),
                "portfolio_volatility": round(portfolio_volatility * 100, 2)
            },
            "position_risks": position_risks,
            "risk_metrics": {
                "portfolio_volatility": round(portfolio_volatility * 100, 2),
                "diversified_volatility": round((diversified_risk / total_capital) * 100, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "var_95": round(var_95, 2),
                "var_99": round(var_99, 2),
                "max_drawdown_expected": round(portfolio_volatility * 2.5 * 100, 2)
            },
            "stress_test_results": stress_results,
            "risk_allocation": {
                "current_risk_budget": round((total_risk / total_capital) * 100, 2),
                "recommended_max": 15.0,
                "risk_utilization": round((total_risk / (total_capital * 0.15)) * 100, 2)
            },
            "recommendations": _generate_portfolio_risk_recommendations(
                portfolio_volatility, sharpe_ratio, position_risks
            )
        }
        
    except Exception as e:
        logger.error(f"❌ [RISK_CALCULATOR] Portfolio risk analysis error: {e}")
        return {"success": False, "error": str(e)}


async def _monte_carlo_simulation(context: Dict[str, Any]) -> Dict[str, Any]:
    """Run Monte Carlo simulation for risk assessment"""
    try:
        initial_capital = context.get("initial_capital", 100000)
        num_trades = context.get("num_trades", 100)
        win_rate = context.get("win_rate", 0.55)
        avg_win = context.get("avg_win", 1.5)
        avg_loss = context.get("avg_loss", 1.0)
        risk_per_trade = context.get("risk_per_trade", 0.02)  # 2% risk
        simulations = context.get("simulations", 1000)
        
        results = []
        
        for _ in range(simulations):
            capital = initial_capital
            equity_curve = [capital]
            
            for _ in range(num_trades):
                if capital <= 0:
                    break
                
                # Risk amount for this trade
                risk_amount = capital * risk_per_trade
                
                # Simulate trade outcome
                if random.random() < win_rate:
                    # Win
                    capital += risk_amount * avg_win
                else:
                    # Loss
                    capital -= risk_amount * avg_loss
                
                equity_curve.append(capital)
            
            # Calculate metrics for this simulation
            max_drawdown = _calculate_max_drawdown(equity_curve)
            final_return = ((capital - initial_capital) / initial_capital) * 100
            
            results.append({
                "final_capital": capital,
                "return": final_return,
                "max_drawdown": max_drawdown,
                "ruin": capital <= initial_capital * 0.5  # 50% drawdown = ruin
            })
        
        # Analyze results
        returns = [r["return"] for r in results]
        drawdowns = [r["max_drawdown"] for r in results]
        ruin_count = sum(1 for r in results if r["ruin"])
        
        # Calculate percentiles
        returns_sorted = sorted(returns)
        percentiles = {
            "5th": returns_sorted[int(simulations * 0.05)],
            "25th": returns_sorted[int(simulations * 0.25)],
            "50th": returns_sorted[int(simulations * 0.50)],
            "75th": returns_sorted[int(simulations * 0.75)],
            "95th": returns_sorted[int(simulations * 0.95)]
        }
        
        return {
            "success": True,
            "simulation_parameters": {
                "initial_capital": initial_capital,
                "num_trades": num_trades,
                "win_rate": round(win_rate * 100, 2),
                "risk_per_trade": round(risk_per_trade * 100, 2),
                "simulations_run": simulations
            },
            "results_summary": {
                "average_return": round(sum(returns) / len(returns), 2),
                "median_return": round(percentiles["50th"], 2),
                "best_return": round(max(returns), 2),
                "worst_return": round(min(returns), 2),
                "average_max_drawdown": round(sum(drawdowns) / len(drawdowns), 2),
                "worst_drawdown": round(max(drawdowns), 2),
                "risk_of_ruin": round((ruin_count / simulations) * 100, 2)
            },
            "return_percentiles": {k: round(v, 2) for k, v in percentiles.items()},
            "risk_assessment": {
                "expected_return": round(sum(returns) / len(returns), 2),
                "return_volatility": round(_calculate_std_dev(returns), 2),
                "sharpe_ratio": round(_calculate_sharpe_ratio(
                    sum(returns) / len(returns) / 100,
                    _calculate_std_dev(returns) / 100,
                    0.02
                ), 2),
                "profit_probability": round(
                    sum(1 for r in returns if r > 0) / simulations * 100, 2
                )
            },
            "recommendations": _generate_monte_carlo_recommendations(
                sum(returns) / len(returns),
                ruin_count / simulations,
                risk_per_trade
            )
        }
        
    except Exception as e:
        logger.error(f"❌ [RISK_CALCULATOR] Monte Carlo simulation error: {e}")
        return {"success": False, "error": str(e)}


async def _optimal_f_calculation(context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate Optimal f for position sizing"""
    try:
        trade_results = context.get("trade_results", [])
        current_capital = context.get("current_capital", 100000)
        
        if not trade_results:
            # Generate sample trade results if none provided
            trade_results = _generate_sample_trades(50)
        
        # Normalize trade results
        biggest_loss = abs(min(trade_results))
        normalized_results = [r / biggest_loss for r in trade_results]
        
        # Search for optimal f
        best_f = 0
        best_twi = 0
        f_values = []
        twi_values = []
        
        for f in range(1, 100):
            f_decimal = f / 100
            twi = 1
            
            for result in normalized_results:
                factor = 1 + (f_decimal * result)
                if factor <= 0:
                    twi = 0
                    break
                twi *= factor
            
            f_values.append(f_decimal)
            twi_values.append(twi)
            
            if twi > best_twi:
                best_twi = twi
                best_f = f_decimal
        
        # Calculate related metrics
        geometric_mean = best_twi ** (1 / len(trade_results))
        
        # Risk metrics at optimal f
        kelly_f = best_f * 0.25  # Typical relationship
        conservative_f = best_f * 0.1
        
        # Position sizes
        position_sizes = {
            "optimal_f": round(current_capital * best_f / biggest_loss, 2),
            "kelly_estimate": round(current_capital * kelly_f / biggest_loss, 2),
            "conservative": round(current_capital * conservative_f / biggest_loss, 2)
        }
        
        return {
            "success": True,
            "optimal_f_analysis": {
                "optimal_f": round(best_f * 100, 2),
                "terminal_wealth_index": round(best_twi, 4),
                "geometric_mean": round((geometric_mean - 1) * 100, 2),
                "biggest_loss": round(biggest_loss, 2)
            },
            "position_sizing": position_sizes,
            "risk_levels": {
                "aggressive": f"{round(best_f * 100, 2)}% (Full Optimal f)",
                "moderate": f"{round(kelly_f * 100, 2)}% (Kelly equivalent)",
                "conservative": f"{round(conservative_f * 100, 2)}% (10% of Optimal f)"
            },
            "trade_statistics": {
                "total_trades": len(trade_results),
                "winning_trades": sum(1 for r in trade_results if r > 0),
                "average_win": round(sum(r for r in trade_results if r > 0) / max(1, sum(1 for r in trade_results if r > 0)), 2),
                "average_loss": round(sum(r for r in trade_results if r < 0) / max(1, sum(1 for r in trade_results if r < 0)), 2)
            },
            "warnings": [
                "Optimal f can be very aggressive",
                "Consider using fraction of optimal f (10-25%)",
                "Past performance doesn't guarantee future results",
                "Account for market regime changes"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [RISK_CALCULATOR] Optimal f calculation error: {e}")
        return {"success": False, "error": str(e)}


# Helper functions
def _fixed_ratio_position_size(balance: float, risk_amount: float) -> Dict[str, Any]:
    """Calculate fixed ratio position size"""
    delta = balance * 0.01  # 1% delta
    contracts = math.sqrt(2 * balance / delta)
    
    return {
        "method": "fixed_ratio",
        "contracts": round(contracts, 2),
        "next_increase_at": round(balance + delta, 2)
    }


def _volatility_based_position_size(balance: float, price: float) -> Dict[str, Any]:
    """Calculate volatility-based position size"""
    volatility = 0.02  # 2% assumed volatility
    target_volatility = 0.01  # 1% target portfolio volatility
    
    position_size = (balance * target_volatility) / (price * volatility)
    
    return {
        "method": "volatility_targeting",
        "position_size": round(position_size, 4),
        "target_volatility": f"{target_volatility * 100}%"
    }


def _atr_based_position_size(balance: float, price: float, risk_pct: float) -> Dict[str, Any]:
    """Calculate ATR-based position size"""
    atr = price * 0.02  # 2% ATR
    risk_amount = balance * (risk_pct / 100)
    position_size = risk_amount / (atr * 2)  # 2x ATR stop
    
    return {
        "method": "atr_based",
        "position_size": round(position_size, 4),
        "stop_distance": round(atr * 2, 2)
    }


def _calculate_risk_reward_ratio(entry: float, stop: float, target: float) -> float:
    """Calculate risk/reward ratio"""
    risk = abs(entry - stop)
    reward = abs(target - entry)
    return reward / risk if risk > 0 else 0


def _check_position_size_warnings(pos_pct: float, risk_pct: float) -> List[str]:
    """Check for position sizing warnings"""
    warnings = []
    
    if pos_pct > 30:
        warnings.append("Position size exceeds 30% of account")
    
    if risk_pct > 2:
        warnings.append("Risk per trade exceeds 2% - consider reducing")
    
    if pos_pct > 50:
        warnings.append("Extremely large position - high concentration risk")
    
    return warnings


def _calculate_stop_hit_probability(entry: float, stop: float, volatility: float) -> float:
    """Estimate probability of stop loss being hit"""
    distance = abs(entry - stop) / entry
    z_score = distance / volatility
    
    # Simplified normal distribution probability
    prob = 0.5 * (1 - math.erf(z_score / math.sqrt(2)))
    return round(prob * 100, 2)


def _estimate_holding_period(volatility: float) -> int:
    """Estimate expected holding period based on volatility"""
    # Higher volatility = shorter holding period
    base_period = 20
    adjustment = 1 / (volatility * 10)
    return max(1, int(base_period * adjustment))


def _calculate_risk_adjusted_return(entry: float, stop: float) -> float:
    """Calculate risk-adjusted return expectation"""
    risk = (entry - stop) / entry
    # Assume 2:1 reward/risk target
    expected_return = risk * 2 * 0.5  # 50% win rate
    return round(expected_return * 100, 2)


def _assess_trade_quality(rr_ratio: float, win_rate: float, expected_value: float) -> str:
    """Assess overall trade quality"""
    score = 0
    
    if rr_ratio >= 2:
        score += 3
    elif rr_ratio >= 1.5:
        score += 2
    elif rr_ratio >= 1:
        score += 1
    
    if win_rate >= 0.6:
        score += 3
    elif win_rate >= 0.5:
        score += 2
    elif win_rate >= 0.4:
        score += 1
    
    if expected_value > 0:
        score += 2
    
    if score >= 7:
        return "excellent"
    elif score >= 5:
        return "good"
    elif score >= 3:
        return "fair"
    else:
        return "poor"


def _calculate_kelly_percentage(win_rate: float, avg_rr: float) -> float:
    """Calculate Kelly percentage for position sizing"""
    if avg_rr == 0:
        return 0
    
    kelly = (win_rate * avg_rr - (1 - win_rate)) / avg_rr
    return max(0, kelly * 100)


def _generate_rr_recommendations(rr_ratio: float, win_rate: float, quality: str) -> List[str]:
    """Generate risk/reward recommendations"""
    recommendations = []
    
    if quality == "excellent":
        recommendations.append("Excellent trade setup - consider full position size")
    elif quality == "good":
        recommendations.append("Good trade setup - use standard position size")
    else:
        recommendations.append("Marginal trade setup - consider reduced position or skip")
    
    if rr_ratio < 1.5:
        recommendations.append("Consider wider profit targets to improve R:R")
    
    if win_rate < 0.4:
        recommendations.append("Low win rate requires higher R:R ratios")
    
    return recommendations


def _calculate_risk_of_ruin(kelly_fraction: float, win_prob: float, target_fraction: float) -> float:
    """Calculate risk of ruin probability"""
    if kelly_fraction <= 0:
        return 1.0
    
    # Simplified risk of ruin calculation
    a = (1 - win_prob) / win_prob
    ror = (a ** (target_fraction / kelly_fraction))
    return min(1.0, ror)


def _calculate_growth_rate(f: float, p: float, b: float) -> float:
    """Calculate expected growth rate"""
    q = 1 - p
    growth = p * math.log(1 + f * b) + q * math.log(1 - f)
    return growth


def _simulate_kelly_outcomes(bankroll: float, f: float, p: float, b: float, trades: int) -> Dict[str, Any]:
    """Simulate Kelly betting outcomes"""
    results = []
    
    for _ in range(100):  # 100 simulations
        capital = bankroll
        for _ in range(trades):
            bet_size = capital * f
            if random.random() < p:
                capital += bet_size * b
            else:
                capital -= bet_size
            
            if capital <= 0:
                capital = 0
                break
        
        results.append(capital)
    
    return {
        "median_outcome": round(sorted(results)[50], 2),
        "best_outcome": round(max(results), 2),
        "worst_outcome": round(min(results), 2),
        "bankruptcy_rate": round(sum(1 for r in results if r == 0) / len(results) * 100, 2)
    }


def _check_kelly_warnings(kelly: float, win_prob: float) -> List[str]:
    """Check for Kelly criterion warnings"""
    warnings = []
    
    if kelly > 0.25:
        warnings.append("Kelly fraction exceeds 25% - very aggressive")
    
    if kelly < 0:
        warnings.append("Negative Kelly - no edge, don't trade")
    
    if win_prob < 0.5 and kelly > 0:
        warnings.append("Positive Kelly with <50% win rate requires high payoff")
    
    return warnings


def _calculate_sharpe_ratio(returns: float, volatility: float, risk_free: float) -> float:
    """Calculate Sharpe ratio"""
    if volatility == 0:
        return 0
    return (returns - risk_free) / volatility


def _calculate_var(capital: float, volatility: float, confidence: float) -> float:
    """Calculate Value at Risk"""
    # Z-scores for confidence levels
    z_scores = {0.95: 1.645, 0.99: 2.326}
    z = z_scores.get(confidence, 1.645)
    
    return capital * volatility * z


def _generate_portfolio_risk_recommendations(volatility: float, sharpe: float, positions: List[Dict]) -> List[str]:
    """Generate portfolio risk recommendations"""
    recommendations = []
    
    if volatility > 0.20:
        recommendations.append("High portfolio volatility - consider risk reduction")
    
    if sharpe < 1:
        recommendations.append("Low Sharpe ratio - improve risk-adjusted returns")
    
    # Check concentration
    if positions:
        max_position = max(p["risk_percentage"] for p in positions)
        if max_position > 5:
            recommendations.append("High single position risk - improve diversification")
    
    return recommendations


def _calculate_max_drawdown(equity_curve: List[float]) -> float:
    """Calculate maximum drawdown from equity curve"""
    if not equity_curve:
        return 0
    
    peak = equity_curve[0]
    max_dd = 0
    
    for value in equity_curve:
        if value > peak:
            peak = value
        
        drawdown = (peak - value) / peak * 100
        max_dd = max(max_dd, drawdown)
    
    return max_dd


def _calculate_std_dev(values: List[float]) -> float:
    """Calculate standard deviation"""
    if not values:
        return 0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)


def _generate_monte_carlo_recommendations(avg_return: float, ruin_rate: float, risk_per_trade: float) -> List[str]:
    """Generate Monte Carlo simulation recommendations"""
    recommendations = []
    
    if avg_return < 0:
        recommendations.append("Negative expected return - review strategy")
    
    if ruin_rate > 0.05:
        recommendations.append("High risk of ruin - reduce position size")
    
    if risk_per_trade > 0.02:
        recommendations.append("Consider reducing risk per trade to 1-2%")
    
    if avg_return > 20 and ruin_rate < 0.01:
        recommendations.append("Strong performance - maintain current approach")
    
    return recommendations


def _generate_sample_trades(count: int) -> List[float]:
    """Generate sample trade results for testing"""
    trades = []
    
    for _ in range(count):
        if random.random() < 0.55:  # 55% win rate
            # Win between 0.5% and 3%
            trades.append(random.uniform(50, 300))
        else:
            # Loss between 0.5% and 2%
            trades.append(-random.uniform(50, 200))
    
    return trades


# Tool metadata for registration
TOOL_METADATA = {
    "name": "risk_calculator_tool",
    "description": "Comprehensive risk assessment and position sizing calculations",
    "version": "1.0.0",
    "author": "Trader Team",
    "capabilities": [
        "position_sizing",
        "stop_loss_calculation",
        "risk_reward_analysis",
        "kelly_criterion",
        "portfolio_risk_analysis",
        "monte_carlo_simulation",
        "optimal_f_calculation"
    ],
    "required_context": [],
    "example_usage": {
        "position_size": {
            "action": "position_size",
            "account_balance": 100000,
            "risk_percentage": 1.0,
            "entry_price": 45000,
            "stop_loss_price": 43500
        },
        "kelly": {
            "action": "kelly",
            "win_probability": 0.55,
            "win_amount": 1.5,
            "loss_amount": 1.0,
            "bankroll": 100000
        },
        "monte_carlo": {
            "action": "monte_carlo",
            "initial_capital": 100000,
            "num_trades": 100,
            "win_rate": 0.55,
            "risk_per_trade": 0.02
        }
    }
}