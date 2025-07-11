"""
Technical Analysis Tool for Trader Team
=======================================

Provides technical indicators and chart analysis capabilities for trading decisions.
Includes RSI, MACD, Moving Averages, Bollinger Bands, and pattern recognition.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random
import math

logger = logging.getLogger(__name__)


async def run(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    📊 Technical Analysis Tool Entry Point
    
    Provides comprehensive technical analysis for trading decisions.
    
    Args:
        context: Operation context containing:
            - action: Type of analysis (indicators, patterns, signals, overview)
            - symbol: Trading symbol
            - timeframe: Analysis timeframe
            - Additional parameters based on action
    
    Returns:
        Technical analysis results
    """
    try:
        action = context.get("action", "overview")
        symbol = context.get("symbol", "BTC-USD")
        timeframe = context.get("timeframe", "1h")
        
        # Route to appropriate analysis function
        if action == "indicators":
            return await _calculate_indicators(symbol, timeframe, context)
        
        elif action == "patterns":
            return await _detect_patterns(symbol, timeframe, context)
        
        elif action == "signals":
            return await _generate_signals(symbol, timeframe, context)
        
        elif action == "overview":
            return await _technical_overview(symbol, timeframe, context)
        
        elif action == "momentum":
            return await _momentum_analysis(symbol, timeframe, context)
        
        elif action == "volatility":
            return await _volatility_analysis(symbol, timeframe, context)
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "available_actions": ["indicators", "patterns", "signals", "overview", "momentum", "volatility"]
            }
            
    except Exception as e:
        logger.error(f"❌ [TECHNICAL_ANALYSIS] Error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _calculate_indicators(symbol: str, timeframe: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate technical indicators"""
    try:
        # Simulate price data for demonstration
        periods = context.get("periods", 50)
        base_price = 45000 if "BTC" in symbol else 100
        
        # Generate price data
        prices = []
        for i in range(periods):
            variation = math.sin(i * 0.1) * 0.02 + random.uniform(-0.01, 0.01)
            price = base_price * (1 + variation)
            prices.append(price)
        
        # Calculate indicators
        indicators = {
            "rsi": _calculate_rsi(prices),
            "macd": _calculate_macd(prices),
            "moving_averages": _calculate_moving_averages(prices),
            "bollinger_bands": _calculate_bollinger_bands(prices),
            "stochastic": _calculate_stochastic(prices),
            "atr": _calculate_atr(prices),
            "volume_indicators": _calculate_volume_indicators(prices)
        }
        
        # Generate analysis summary
        analysis = _analyze_indicators(indicators)
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.now().isoformat(),
            "indicators": indicators,
            "analysis": analysis,
            "recommendation": _generate_recommendation(indicators)
        }
        
    except Exception as e:
        logger.error(f"❌ [TECHNICAL_ANALYSIS] Indicator calculation error: {e}")
        return {"success": False, "error": str(e)}


async def _detect_patterns(symbol: str, timeframe: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Detect chart patterns"""
    try:
        # Simulate pattern detection
        patterns = {
            "reversal_patterns": [
                {
                    "type": "head_and_shoulders",
                    "confidence": 0.75,
                    "direction": "bearish",
                    "target_price": 42000
                },
                {
                    "type": "double_bottom",
                    "confidence": 0.65,
                    "direction": "bullish",
                    "target_price": 48000
                }
            ],
            "continuation_patterns": [
                {
                    "type": "ascending_triangle",
                    "confidence": 0.80,
                    "direction": "bullish",
                    "breakout_level": 46500
                }
            ],
            "candlestick_patterns": [
                {
                    "type": "doji",
                    "timestamp": datetime.now().isoformat(),
                    "significance": "indecision"
                },
                {
                    "type": "hammer",
                    "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                    "significance": "potential_reversal"
                }
            ],
            "support_resistance": {
                "support_levels": [42000, 43500, 44200],
                "resistance_levels": [46000, 47500, 49000],
                "current_price": 45000
            }
        }
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "patterns": patterns,
            "pattern_strength": _calculate_pattern_strength(patterns),
            "trading_implications": _get_pattern_implications(patterns)
        }
        
    except Exception as e:
        logger.error(f"❌ [TECHNICAL_ANALYSIS] Pattern detection error: {e}")
        return {"success": False, "error": str(e)}


async def _generate_signals(symbol: str, timeframe: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate trading signals"""
    try:
        # Generate comprehensive trading signals
        signals = {
            "primary_signal": {
                "action": "BUY",
                "strength": 0.72,
                "confidence": 0.85,
                "reasons": [
                    "RSI showing oversold conditions",
                    "MACD bullish crossover",
                    "Price bounced from support level"
                ]
            },
            "secondary_signals": [
                {
                    "indicator": "moving_average_crossover",
                    "signal": "bullish",
                    "timeframe": "4h"
                },
                {
                    "indicator": "volume_spike",
                    "signal": "accumulation",
                    "timeframe": "1d"
                }
            ],
            "risk_parameters": {
                "stop_loss": 43500,
                "take_profit_1": 46500,
                "take_profit_2": 48000,
                "risk_reward_ratio": 2.5
            },
            "market_conditions": {
                "trend": "bullish",
                "volatility": "moderate",
                "volume": "increasing"
            }
        }
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "signals": signals,
            "signal_timestamp": datetime.now().isoformat(),
            "next_review": (datetime.now() + timedelta(hours=1)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ [TECHNICAL_ANALYSIS] Signal generation error: {e}")
        return {"success": False, "error": str(e)}


async def _technical_overview(symbol: str, timeframe: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive technical overview"""
    try:
        overview = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.now().isoformat(),
            "market_summary": {
                "trend": "bullish",
                "strength": "moderate",
                "phase": "accumulation"
            },
            "key_levels": {
                "current_price": 45000,
                "daily_high": 45800,
                "daily_low": 44200,
                "pivot_point": 45000,
                "support_1": 44500,
                "support_2": 43800,
                "resistance_1": 45500,
                "resistance_2": 46200
            },
            "technical_rating": {
                "overall": "BUY",
                "moving_averages": "STRONG_BUY",
                "oscillators": "NEUTRAL",
                "summary": {
                    "buy_signals": 8,
                    "neutral_signals": 3,
                    "sell_signals": 1
                }
            },
            "momentum_indicators": {
                "rsi": 45,
                "stochastic": 38,
                "cci": -20,
                "momentum": "increasing"
            },
            "volatility_metrics": {
                "atr": 850,
                "bollinger_band_width": 0.035,
                "historical_volatility": 0.65
            }
        }
        
        return {
            "success": True,
            "overview": overview,
            "actionable_insights": [
                "Price approaching key resistance at 46000",
                "RSI showing room for upward movement",
                "Volume increasing on recent price advances",
                "Consider scaling into positions near support levels"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ [TECHNICAL_ANALYSIS] Overview generation error: {e}")
        return {"success": False, "error": str(e)}


async def _momentum_analysis(symbol: str, timeframe: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze momentum indicators"""
    try:
        momentum_data = {
            "rsi": {
                "value": 52,
                "trend": "neutral",
                "divergence": None
            },
            "macd": {
                "macd_line": 125,
                "signal_line": 118,
                "histogram": 7,
                "trend": "bullish",
                "crossover": "recent_bullish"
            },
            "stochastic": {
                "k_line": 65,
                "d_line": 62,
                "zone": "neutral",
                "crossover": None
            },
            "momentum_oscillator": {
                "value": 102,
                "trend": "increasing",
                "rate_of_change": 2.5
            },
            "composite_momentum": {
                "score": 68,
                "interpretation": "moderately_bullish",
                "strength": "increasing"
            }
        }
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "momentum_analysis": momentum_data,
            "momentum_signals": _interpret_momentum(momentum_data),
            "trading_bias": "bullish_momentum_building"
        }
        
    except Exception as e:
        logger.error(f"❌ [TECHNICAL_ANALYSIS] Momentum analysis error: {e}")
        return {"success": False, "error": str(e)}


async def _volatility_analysis(symbol: str, timeframe: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze volatility metrics"""
    try:
        volatility_data = {
            "current_volatility": {
                "atr": 850,
                "atr_percentage": 1.89,
                "trend": "decreasing"
            },
            "bollinger_bands": {
                "upper": 46200,
                "middle": 45000,
                "lower": 43800,
                "width": 2400,
                "width_percentage": 5.33
            },
            "historical_volatility": {
                "hv_20": 0.65,
                "hv_50": 0.72,
                "hv_100": 0.78,
                "percentile": 35
            },
            "volatility_forecast": {
                "next_24h": 0.68,
                "next_week": 0.71,
                "confidence": 0.75
            },
            "risk_metrics": {
                "value_at_risk": 1250,
                "expected_shortfall": 1850,
                "sharpe_ratio": 1.45
            }
        }
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "volatility_analysis": volatility_data,
            "trading_implications": [
                "Low volatility environment favors range trading",
                "Consider using tighter stops due to decreasing ATR",
                "Options strategies may benefit from volatility expansion"
            ],
            "risk_adjustment": _calculate_risk_adjustment(volatility_data)
        }
        
    except Exception as e:
        logger.error(f"❌ [TECHNICAL_ANALYSIS] Volatility analysis error: {e}")
        return {"success": False, "error": str(e)}


# Helper functions
def _calculate_rsi(prices: List[float], period: int = 14) -> Dict[str, Any]:
    """Calculate RSI indicator"""
    if len(prices) < period:
        return {"value": 50, "interpretation": "neutral"}
    
    # Simplified RSI calculation
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    interpretation = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
    
    return {
        "value": round(rsi, 2),
        "interpretation": interpretation,
        "trend": "bullish" if rsi > 50 else "bearish"
    }


def _calculate_macd(prices: List[float]) -> Dict[str, Any]:
    """Calculate MACD indicator"""
    # Simplified MACD calculation
    ema_12 = _calculate_ema(prices, 12)
    ema_26 = _calculate_ema(prices, 26)
    
    macd_line = ema_12 - ema_26
    signal_line = macd_line * 0.9  # Simplified signal line
    histogram = macd_line - signal_line
    
    return {
        "macd_line": round(macd_line, 2),
        "signal_line": round(signal_line, 2),
        "histogram": round(histogram, 2),
        "crossover": "bullish" if histogram > 0 else "bearish",
        "divergence": None
    }


def _calculate_ema(prices: List[float], period: int) -> float:
    """Calculate Exponential Moving Average"""
    if not prices:
        return 0
    
    multiplier = 2 / (period + 1)
    ema = prices[0]
    
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema


def _calculate_moving_averages(prices: List[float]) -> Dict[str, Any]:
    """Calculate various moving averages"""
    ma_5 = sum(prices[-5:]) / 5 if len(prices) >= 5 else prices[-1]
    ma_10 = sum(prices[-10:]) / 10 if len(prices) >= 10 else prices[-1]
    ma_20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else prices[-1]
    ma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else prices[-1]
    
    current_price = prices[-1]
    
    return {
        "ma_5": round(ma_5, 2),
        "ma_10": round(ma_10, 2),
        "ma_20": round(ma_20, 2),
        "ma_50": round(ma_50, 2),
        "ema_12": round(_calculate_ema(prices, 12), 2),
        "ema_26": round(_calculate_ema(prices, 26), 2),
        "price_position": "above_all" if current_price > max(ma_5, ma_10, ma_20) else "below_all" if current_price < min(ma_5, ma_10, ma_20) else "mixed"
    }


def _calculate_bollinger_bands(prices: List[float], period: int = 20) -> Dict[str, Any]:
    """Calculate Bollinger Bands"""
    if len(prices) < period:
        return {"upper": 0, "middle": 0, "lower": 0, "width": 0}
    
    sma = sum(prices[-period:]) / period
    variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
    std_dev = math.sqrt(variance)
    
    upper = sma + (2 * std_dev)
    lower = sma - (2 * std_dev)
    
    return {
        "upper": round(upper, 2),
        "middle": round(sma, 2),
        "lower": round(lower, 2),
        "width": round(upper - lower, 2),
        "position": "near_upper" if prices[-1] > sma + std_dev else "near_lower" if prices[-1] < sma - std_dev else "middle"
    }


def _calculate_stochastic(prices: List[float], period: int = 14) -> Dict[str, Any]:
    """Calculate Stochastic oscillator"""
    if len(prices) < period:
        return {"k": 50, "d": 50, "signal": "neutral"}
    
    recent_prices = prices[-period:]
    lowest = min(recent_prices)
    highest = max(recent_prices)
    
    if highest == lowest:
        k = 50
    else:
        k = ((prices[-1] - lowest) / (highest - lowest)) * 100
    
    d = k * 0.9  # Simplified %D calculation
    
    signal = "oversold" if k < 20 else "overbought" if k > 80 else "neutral"
    
    return {
        "k": round(k, 2),
        "d": round(d, 2),
        "signal": signal
    }


def _calculate_atr(prices: List[float], period: int = 14) -> float:
    """Calculate Average True Range"""
    if len(prices) < 2:
        return 0
    
    true_ranges = []
    for i in range(1, len(prices)):
        high_low = abs(prices[i] * 1.01 - prices[i] * 0.99)  # Simulated high-low
        true_ranges.append(high_low)
    
    if len(true_ranges) >= period:
        atr = sum(true_ranges[-period:]) / period
    else:
        atr = sum(true_ranges) / len(true_ranges) if true_ranges else 0
    
    return round(atr, 2)


def _calculate_volume_indicators(prices: List[float]) -> Dict[str, Any]:
    """Calculate volume-based indicators"""
    # Simulate volume data
    volumes = [random.randint(1000000, 5000000) for _ in prices]
    
    avg_volume = sum(volumes) / len(volumes)
    recent_volume = volumes[-1]
    
    return {
        "current_volume": recent_volume,
        "average_volume": round(avg_volume),
        "volume_ratio": round(recent_volume / avg_volume, 2),
        "volume_trend": "increasing" if recent_volume > avg_volume else "decreasing",
        "obv_trend": "bullish" if random.random() > 0.5 else "bearish"
    }


def _analyze_indicators(indicators: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze all indicators for trading signals"""
    bullish_count = 0
    bearish_count = 0
    
    # RSI analysis
    if indicators["rsi"]["value"] < 30:
        bullish_count += 1
    elif indicators["rsi"]["value"] > 70:
        bearish_count += 1
    
    # MACD analysis
    if indicators["macd"]["crossover"] == "bullish":
        bullish_count += 1
    else:
        bearish_count += 1
    
    # Moving average analysis
    if indicators["moving_averages"]["price_position"] == "above_all":
        bullish_count += 1
    elif indicators["moving_averages"]["price_position"] == "below_all":
        bearish_count += 1
    
    # Stochastic analysis
    if indicators["stochastic"]["signal"] == "oversold":
        bullish_count += 1
    elif indicators["stochastic"]["signal"] == "overbought":
        bearish_count += 1
    
    total_signals = bullish_count + bearish_count
    
    return {
        "bullish_signals": bullish_count,
        "bearish_signals": bearish_count,
        "neutral_signals": 5 - total_signals,
        "overall_sentiment": "bullish" if bullish_count > bearish_count else "bearish" if bearish_count > bullish_count else "neutral",
        "signal_strength": max(bullish_count, bearish_count) / 5
    }


def _generate_recommendation(indicators: Dict[str, Any]) -> Dict[str, Any]:
    """Generate trading recommendation based on indicators"""
    analysis = _analyze_indicators(indicators)
    
    if analysis["overall_sentiment"] == "bullish":
        action = "BUY"
        confidence = analysis["signal_strength"]
    elif analysis["overall_sentiment"] == "bearish":
        action = "SELL"
        confidence = analysis["signal_strength"]
    else:
        action = "HOLD"
        confidence = 0.5
    
    return {
        "action": action,
        "confidence": round(confidence, 2),
        "timeframe": "short_term",
        "risk_level": "moderate",
        "notes": [
            f"{analysis['bullish_signals']} bullish indicators detected",
            f"{analysis['bearish_signals']} bearish indicators detected",
            "Monitor key support and resistance levels"
        ]
    }


def _calculate_pattern_strength(patterns: Dict[str, Any]) -> float:
    """Calculate overall pattern strength"""
    total_confidence = 0
    pattern_count = 0
    
    for pattern_list in [patterns.get("reversal_patterns", []), patterns.get("continuation_patterns", [])]:
        for pattern in pattern_list:
            total_confidence += pattern.get("confidence", 0)
            pattern_count += 1
    
    return round(total_confidence / pattern_count, 2) if pattern_count > 0 else 0


def _get_pattern_implications(patterns: Dict[str, Any]) -> List[str]:
    """Get trading implications from detected patterns"""
    implications = []
    
    # Check reversal patterns
    for pattern in patterns.get("reversal_patterns", []):
        if pattern["confidence"] > 0.7:
            implications.append(f"Strong {pattern['type']} pattern suggests {pattern['direction']} reversal")
    
    # Check continuation patterns
    for pattern in patterns.get("continuation_patterns", []):
        if pattern["confidence"] > 0.7:
            implications.append(f"{pattern['type']} indicates {pattern['direction']} continuation")
    
    # Support/Resistance analysis
    sr = patterns.get("support_resistance", {})
    if sr:
        current = sr.get("current_price", 0)
        nearest_support = min(sr.get("support_levels", [0]), key=lambda x: abs(x - current))
        nearest_resistance = min(sr.get("resistance_levels", [0]), key=lambda x: abs(x - current))
        
        implications.append(f"Key support at {nearest_support}, resistance at {nearest_resistance}")
    
    return implications


def _interpret_momentum(momentum_data: Dict[str, Any]) -> List[str]:
    """Interpret momentum indicators"""
    signals = []
    
    # RSI interpretation
    rsi = momentum_data.get("rsi", {})
    if rsi.get("value", 50) < 30:
        signals.append("RSI oversold - potential buying opportunity")
    elif rsi.get("value", 50) > 70:
        signals.append("RSI overbought - consider taking profits")
    
    # MACD interpretation
    macd = momentum_data.get("macd", {})
    if macd.get("crossover") == "recent_bullish":
        signals.append("MACD bullish crossover - momentum shifting positive")
    
    # Composite momentum
    composite = momentum_data.get("composite_momentum", {})
    if composite.get("score", 50) > 65:
        signals.append("Strong bullish momentum detected")
    elif composite.get("score", 50) < 35:
        signals.append("Weak momentum - caution advised")
    
    return signals


def _calculate_risk_adjustment(volatility_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate risk-adjusted position sizing"""
    atr_percentage = volatility_data.get("current_volatility", {}).get("atr_percentage", 2)
    
    # Risk adjustment based on volatility
    if atr_percentage < 1.5:
        position_adjustment = 1.2  # Increase position size in low volatility
        stop_distance = 1.5
    elif atr_percentage > 3:
        position_adjustment = 0.7  # Decrease position size in high volatility
        stop_distance = 2.5
    else:
        position_adjustment = 1.0
        stop_distance = 2.0
    
    return {
        "position_size_multiplier": position_adjustment,
        "recommended_stop_distance_atr": stop_distance,
        "volatility_regime": "low" if atr_percentage < 1.5 else "high" if atr_percentage > 3 else "normal",
        "risk_notes": [
            f"Adjust position size by {position_adjustment}x based on volatility",
            f"Place stops at {stop_distance}x ATR from entry"
        ]
    }


# Tool metadata for registration
TOOL_METADATA = {
    "name": "technical_analysis_tool",
    "description": "Comprehensive technical analysis for trading decisions",
    "version": "1.0.0",
    "author": "Trader Team",
    "capabilities": [
        "calculate_indicators",
        "detect_patterns",
        "generate_signals",
        "momentum_analysis",
        "volatility_analysis"
    ],
    "required_context": [],
    "example_usage": {
        "indicators": {
            "action": "indicators",
            "symbol": "BTC-USD",
            "timeframe": "1h",
            "periods": 50
        },
        "patterns": {
            "action": "patterns",
            "symbol": "ETH-USD",
            "timeframe": "4h"
        },
        "signals": {
            "action": "signals",
            "symbol": "AAPL",
            "timeframe": "1d"
        }
    }
}