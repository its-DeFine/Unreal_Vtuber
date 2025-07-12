"""
Trading Analysis Tool for Trader Team.

Provides advanced trading analysis including pattern recognition,
indicator calculations, and strategy recommendations.
"""

import asyncio
import json
import math
from datetime import datetime
from typing import Dict, Any, List, Optional

from ..base_tool import BaseTool, ToolResult, ToolStatus, ToolParameter, ToolExecutionContext


class TradingAnalysisTool(BaseTool):
    """
    Advanced trading analysis tool for pattern recognition and strategy development.
    
    Analyzes market patterns, calculates technical indicators, and provides
    trading strategy recommendations based on technical analysis.
    """
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="price_data",
                type="string",
                description="JSON string of price data with timestamps and prices",
                required=True
            ),
            ToolParameter(
                name="analysis_type",
                type="string",
                description="Type of analysis to perform",
                required=False,
                default="comprehensive",
                enum=["technical_indicators", "pattern_recognition", "trend_analysis", "comprehensive"]
            ),
            ToolParameter(
                name="timeframe",
                type="string",
                description="Analysis timeframe",
                required=False,
                default="1d",
                enum=["5m", "15m", "1h", "4h", "1d", "1w"]
            )
        ]
        
        super().__init__(
            name="trading_analysis",
            description="Perform advanced trading analysis including technical indicators and pattern recognition",
            parameters=parameters,
            timeout=20.0
        )
    
    async def execute(
        self,
        context: ToolExecutionContext,
        price_data: str,
        analysis_type: str = "comprehensive",
        timeframe: str = "1d",
        **kwargs
    ) -> ToolResult:
        """Execute trading analysis"""
        
        try:
            # Parse price data
            try:
                data = json.loads(price_data)
                prices = [float(p["price"]) for p in data if "price" in p]
                volumes = [float(p.get("volume", 0)) for p in data if "price" in p]
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                return ToolResult(
                    success=False,
                    status=ToolStatus.FAILED,
                    error_message=f"Invalid price data format: {str(e)}"
                )
            
            if len(prices) < 10:
                return ToolResult(
                    success=False,
                    status=ToolStatus.FAILED,
                    error_message="Insufficient price data for analysis (minimum 10 points required)"
                )
            
            # Simulate analysis processing time
            await asyncio.sleep(1.0)
            
            # Perform analysis based on type
            result = {}
            
            if analysis_type in ["technical_indicators", "comprehensive"]:
                result["technical_indicators"] = self._calculate_technical_indicators(prices, volumes)
            
            if analysis_type in ["pattern_recognition", "comprehensive"]:
                result["patterns"] = self._recognize_patterns(prices)
            
            if analysis_type in ["trend_analysis", "comprehensive"]:
                result["trend_analysis"] = self._analyze_trends(prices)
            
            if analysis_type == "comprehensive":
                result["trading_signals"] = self._generate_trading_signals(
                    result["technical_indicators"],
                    result["patterns"],
                    result["trend_analysis"]
                )
                result["risk_assessment"] = self._assess_risk(prices, result["technical_indicators"])
            
            # Add metadata
            result["analysis_metadata"] = {
                "data_points": len(prices),
                "timeframe": timeframe,
                "analysis_type": analysis_type,
                "current_price": prices[-1],
                "price_range": {
                    "min": min(prices),
                    "max": max(prices),
                    "range_percent": ((max(prices) - min(prices)) / min(prices)) * 100
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return ToolResult(
                success=True,
                status=ToolStatus.SUCCESS,
                result=result,
                metadata={
                    "tool": "trading_analysis",
                    "analysis_type": analysis_type,
                    "data_points": len(prices)
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                status=ToolStatus.FAILED,
                error_message=f"Trading analysis failed: {str(e)}"
            )
    
    def _calculate_technical_indicators(self, prices: List[float], volumes: List[float]) -> Dict[str, Any]:
        """Calculate various technical indicators"""
        
        indicators = {}
        
        # Moving Averages
        indicators["sma"] = {}
        for period in [5, 10, 20, 50]:
            if len(prices) >= period:
                sma = sum(prices[-period:]) / period
                indicators["sma"][f"sma_{period}"] = round(sma, 2)
        
        # Exponential Moving Average (simplified)
        if len(prices) >= 12:
            ema_12 = self._calculate_ema(prices, 12)
            ema_26 = self._calculate_ema(prices, 26)
            indicators["ema"] = {
                "ema_12": round(ema_12, 2),
                "ema_26": round(ema_26, 2)
            }
            
            # MACD
            macd_line = ema_12 - ema_26
            signal_line = self._calculate_ema([macd_line], 9) if len(prices) >= 35 else macd_line
            indicators["macd"] = {
                "macd_line": round(macd_line, 4),
                "signal_line": round(signal_line, 4),
                "histogram": round(macd_line - signal_line, 4)
            }
        
        # RSI (Relative Strength Index)
        if len(prices) >= 14:
            rsi = self._calculate_rsi(prices, 14)
            indicators["rsi"] = {
                "value": round(rsi, 2),
                "interpretation": "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
            }
        
        # Bollinger Bands
        if len(prices) >= 20:
            bb = self._calculate_bollinger_bands(prices, 20, 2)
            indicators["bollinger_bands"] = bb
        
        # Volume indicators
        if volumes and any(v > 0 for v in volumes):
            indicators["volume"] = {
                "average_volume": round(sum(volumes[-20:]) / min(20, len(volumes)), 0),
                "current_volume": volumes[-1] if volumes else 0,
                "volume_trend": "increasing" if len(volumes) >= 2 and volumes[-1] > volumes[-2] else "decreasing"
            }
        
        return indicators
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return sum(prices) / len(prices)
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # Start with SMA
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral value
        
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
        
        if len(gains) < period:
            return 50.0
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            middle = sum(prices) / len(prices)
            return {
                "upper": round(middle * 1.1, 2),
                "middle": round(middle, 2),
                "lower": round(middle * 0.9, 2)
            }
        
        recent_prices = prices[-period:]
        middle = sum(recent_prices) / period
        
        # Calculate standard deviation
        variance = sum((p - middle) ** 2 for p in recent_prices) / period
        std = math.sqrt(variance)
        
        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        
        return {
            "upper": round(upper, 2),
            "middle": round(middle, 2),
            "lower": round(lower, 2),
            "width": round(((upper - lower) / middle) * 100, 2)
        }
    
    def _recognize_patterns(self, prices: List[float]) -> Dict[str, Any]:
        """Recognize chart patterns"""
        patterns = []
        
        if len(prices) < 10:
            return {"patterns": patterns, "count": 0}
        
        # Simple pattern recognition
        recent_prices = prices[-10:]
        
        # Trend patterns
        if all(recent_prices[i] <= recent_prices[i+1] for i in range(len(recent_prices)-1)):
            patterns.append({
                "type": "ascending_trend",
                "strength": "strong",
                "description": "Strong upward trend detected"
            })
        elif all(recent_prices[i] >= recent_prices[i+1] for i in range(len(recent_prices)-1)):
            patterns.append({
                "type": "descending_trend", 
                "strength": "strong",
                "description": "Strong downward trend detected"
            })
        
        # Support/Resistance
        current_price = prices[-1]
        recent_highs = [p for p in recent_prices if p > current_price * 0.99]
        recent_lows = [p for p in recent_prices if p < current_price * 1.01]
        
        if len(recent_highs) >= 3:
            patterns.append({
                "type": "resistance_level",
                "level": round(max(recent_highs), 2),
                "description": "Price approaching resistance level"
            })
        
        if len(recent_lows) >= 3:
            patterns.append({
                "type": "support_level",
                "level": round(min(recent_lows), 2),
                "description": "Price approaching support level"
            })
        
        # Volatility patterns
        price_changes = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        avg_change = sum(price_changes) / len(price_changes)
        recent_volatility = sum(price_changes[-5:]) / 5
        
        if recent_volatility > avg_change * 1.5:
            patterns.append({
                "type": "high_volatility",
                "description": "Increased volatility detected"
            })
        
        return {
            "patterns": patterns,
            "count": len(patterns),
            "volatility_score": round(recent_volatility / avg_change, 2) if avg_change > 0 else 1.0
        }
    
    def _analyze_trends(self, prices: List[float]) -> Dict[str, Any]:
        """Analyze price trends"""
        if len(prices) < 5:
            return {"error": "Insufficient data for trend analysis"}
        
        # Short-term trend (last 5 periods)
        short_trend = "bullish" if prices[-1] > prices[-5] else "bearish"
        short_strength = abs(prices[-1] - prices[-5]) / prices[-5] * 100
        
        # Medium-term trend (last 20 periods or available)
        lookback = min(20, len(prices))
        medium_trend = "bullish" if prices[-1] > prices[-lookback] else "bearish"
        medium_strength = abs(prices[-1] - prices[-lookback]) / prices[-lookback] * 100
        
        # Trend momentum
        recent_changes = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(max(1, len(prices)-10), len(prices))]
        momentum = sum(recent_changes) / len(recent_changes) * 100
        
        return {
            "short_term": {
                "direction": short_trend,
                "strength_percent": round(short_strength, 2)
            },
            "medium_term": {
                "direction": medium_trend,
                "strength_percent": round(medium_strength, 2)
            },
            "momentum": {
                "value": round(momentum, 4),
                "interpretation": "strong_bullish" if momentum > 0.5 else "bullish" if momentum > 0 else "bearish" if momentum > -0.5 else "strong_bearish"
            },
            "trend_consistency": self._calculate_trend_consistency(prices)
        }
    
    def _calculate_trend_consistency(self, prices: List[float]) -> float:
        """Calculate how consistent the trend is"""
        if len(prices) < 10:
            return 0.5
        
        # Count directional changes
        changes = [(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        direction_changes = sum(1 for i in range(1, len(changes)) if (changes[i] > 0) != (changes[i-1] > 0))
        
        # More direction changes = less consistent
        consistency = max(0, 1 - (direction_changes / len(changes)))
        return round(consistency, 2)
    
    def _generate_trading_signals(self, indicators: Dict, patterns: Dict, trends: Dict) -> List[Dict[str, Any]]:
        """Generate trading signals based on analysis"""
        signals = []
        
        # RSI signals
        if "rsi" in indicators and indicators["rsi"]["value"]:
            rsi_value = indicators["rsi"]["value"]
            if rsi_value < 30:
                signals.append({
                    "type": "buy",
                    "strength": "moderate",
                    "reason": "RSI oversold condition",
                    "indicator": "RSI",
                    "value": rsi_value
                })
            elif rsi_value > 70:
                signals.append({
                    "type": "sell",
                    "strength": "moderate", 
                    "reason": "RSI overbought condition",
                    "indicator": "RSI",
                    "value": rsi_value
                })
        
        # Trend signals
        if trends and "momentum" in trends:
            momentum = trends["momentum"]["interpretation"]
            if momentum in ["strong_bullish", "bullish"]:
                signals.append({
                    "type": "buy",
                    "strength": "strong" if momentum == "strong_bullish" else "moderate",
                    "reason": f"Strong positive momentum detected",
                    "indicator": "momentum",
                    "value": trends["momentum"]["value"]
                })
            elif momentum in ["strong_bearish", "bearish"]:
                signals.append({
                    "type": "sell",
                    "strength": "strong" if momentum == "strong_bearish" else "moderate",
                    "reason": f"Strong negative momentum detected",
                    "indicator": "momentum",
                    "value": trends["momentum"]["value"]
                })
        
        # Pattern signals
        if patterns and patterns["patterns"]:
            for pattern in patterns["patterns"]:
                if pattern["type"] == "ascending_trend":
                    signals.append({
                        "type": "buy",
                        "strength": "moderate",
                        "reason": "Ascending trend pattern detected",
                        "indicator": "pattern",
                        "value": pattern["type"]
                    })
                elif pattern["type"] == "descending_trend":
                    signals.append({
                        "type": "sell",
                        "strength": "moderate",
                        "reason": "Descending trend pattern detected",
                        "indicator": "pattern",
                        "value": pattern["type"]
                    })
        
        return signals
    
    def _assess_risk(self, prices: List[float], indicators: Dict) -> Dict[str, Any]:
        """Assess trading risk based on analysis"""
        risk_factors = []
        risk_score = 0  # 0-100 scale
        
        # Volatility risk
        if len(prices) >= 10:
            recent_prices = prices[-10:]
            volatility = self._calculate_volatility(recent_prices)
            
            if volatility > 5:
                risk_factors.append("High volatility detected")
                risk_score += 30
            elif volatility > 2:
                risk_factors.append("Moderate volatility")
                risk_score += 15
        
        # RSI risk
        if "rsi" in indicators and indicators["rsi"]["value"]:
            rsi_value = indicators["rsi"]["value"]
            if rsi_value > 80 or rsi_value < 20:
                risk_factors.append("Extreme RSI levels")
                risk_score += 25
        
        # Price movement risk
        if len(prices) >= 2:
            recent_change = abs(prices[-1] - prices[-2]) / prices[-2] * 100
            if recent_change > 10:
                risk_factors.append("Large recent price movement")
                risk_score += 20
        
        # Determine risk level
        if risk_score < 25:
            risk_level = "low"
        elif risk_score < 50:
            risk_level = "moderate"
        elif risk_score < 75:
            risk_level = "high"
        else:
            risk_level = "very_high"
        
        return {
            "risk_level": risk_level,
            "risk_score": min(risk_score, 100),
            "risk_factors": risk_factors,
            "recommendations": self._get_risk_recommendations(risk_level, risk_factors)
        }
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility as percentage"""
        if len(prices) < 2:
            return 0
        
        changes = [(prices[i] - prices[i-1]) / prices[i-1] * 100 for i in range(1, len(prices))]
        avg_change = sum(changes) / len(changes)
        variance = sum((change - avg_change) ** 2 for change in changes) / len(changes)
        
        return math.sqrt(variance)
    
    def _get_risk_recommendations(self, risk_level: str, risk_factors: List[str]) -> List[str]:
        """Get risk management recommendations"""
        recommendations = []
        
        if risk_level in ["high", "very_high"]:
            recommendations.append("Consider reducing position size")
            recommendations.append("Set tight stop-loss orders")
            recommendations.append("Monitor positions closely")
        
        if "High volatility" in " ".join(risk_factors):
            recommendations.append("Use volatility-adjusted position sizing")
            
        if "Extreme RSI levels" in " ".join(risk_factors):
            recommendations.append("Wait for RSI to normalize before entering")
        
        if not recommendations:
            recommendations.append("Standard risk management applies")
        
        return recommendations


# Register the tool
from ..tool_catalog import register_tool

register_tool(
    TradingAnalysisTool,
    category="financial",
    team_types=["trader"],
    priority=9
)