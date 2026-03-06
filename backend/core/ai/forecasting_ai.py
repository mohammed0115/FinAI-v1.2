"""
Forecasting AI Module

Enhances financial forecasting with AI-powered explanations, trend analysis,
and intelligent prediction commentary.

Features:
- Trend explanation and analysis
- Forecast commentary generation
- Influencing factors identification
- Risk indicators extraction
- Turning point detection
- Bilingual explanations (Arabic/English)
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.ai.client import get_openai_client
from core.ai.errors import AIAPIError

logger = logging.getLogger(__name__)


class ForecastingAI:
    """
    Provides AI-enhanced forecasting with intelligent explanations,
    trend analysis, and prediction interpretation.
    """

    def __init__(self):
        self.client = get_openai_client()
        self.model = 'gpt-4o-mini'

    def analyze_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_data: List[Dict[str, Any]],
        metric_name: str,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Analyze forecast and provide AI-powered insights.

        Args:
            historical_data: List of historical data points [{'date': '', 'value': 0}, ...]
            forecast_data: List of forecast data points [{'date': '', 'value': 0, 'confidence': 0.9}, ...]
            metric_name: Name of metric (revenue, expenses, etc.)
            language: Target language ('ar' or 'en')

        Returns:
            Dict with:
            - trend_explanation: Why trend is moving in this direction
            - forecast_summary: High-level forecast summary
            - key_factors: Influencing factors
            - risk_indicators: Potential risks
            - turning_points: Detected turning points
            - recommendations: Actionable recommendations
            - confidence_assessment: Confidence in forecast
            - language: Response language
            - timestamp: Processing timestamp
        """
        try:
            start_time = datetime.utcnow()

            # Analyze historical trend
            trend_analysis = self._analyze_trend(
                historical_data, metric_name, language
            )

            # Generate forecast explanation
            forecast_explanation = self._explain_forecast(
                historical_data, forecast_data, metric_name, language
            )

            # Identify key factors
            key_factors = self._identify_factors(
                historical_data, forecast_data, metric_name, language
            )

            # Detect anomalies and turning points
            turning_points = self._detect_turning_points(
                historical_data, forecast_data
            )

            # Assess risks
            risk_assessment = self._assess_forecast_risks(
                forecast_data, trend_analysis, language
            )

            # Generate recommendations
            recommendations = self._generate_recommendations(
                trend_analysis,
                forecast_explanation,
                risk_assessment,
                language
            )

            result = {
                'metric': metric_name,
                'trend_direction': trend_analysis['direction'],
                'trend_strength': trend_analysis['strength'],
                'trend_explanation': trend_analysis['explanation'],
                'forecast_summary': forecast_explanation['summary'],
                'forecast_period_days': len(forecast_data),
                'expected_change': forecast_explanation.get('expected_change', 'unknown'),
                'change_percentage': forecast_explanation.get('change_percentage'),
                'key_factors': key_factors,
                'turning_points': turning_points,
                'risk_level': risk_assessment['risk_level'],
                'risk_indicators': risk_assessment['indicators'],
                'confidence_score': forecast_explanation.get('confidence', 0.5),
                'recommendations': recommendations,
                'affected_areas': self._identify_affected_areas(metric_name),
                'language': language,
                'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000),
                'timestamp': start_time.isoformat()
            }

            logger.info(f"Forecast analysis completed for {metric_name}")
            return result

        except Exception as e:
            logger.error(f"Forecast analysis error: {str(e)}", exc_info=True)
            raise AIAPIError(f"Forecast analysis failed: {str(e)}")

    def _analyze_trend(
        self,
        historical_data: List[Dict[str, Any]],
        metric_name: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze historical trend."""
        if len(historical_data) < 2:
            return {
                'direction': 'insufficient_data',
                'strength': 0,
                'explanation': 'Not enough historical data'
            }

        values = [d.get('value', 0) for d in historical_data if 'value' in d]
        if not values:
            return {
                'direction': 'unknown',
                'strength': 0,
                'explanation': 'No numeric values found'
            }

        # Simple trend calculation
        first_value = values[0]
        last_value = values[-1]
        change = last_value - first_value

        if first_value == 0:
            change_pct = 0
            direction = 'stable'
            strength = 0
        else:
            change_pct = (change / abs(first_value)) * 100
            direction = 'increasing' if change > 0 else 'decreasing' if change < 0 else 'stable'
            strength = min(abs(change_pct) / 10, 1.0)  # Normalize to 0-1

        prompt = f"""Analyze the trend for {metric_name}.

Historical Data Points: {len(historical_data)}
First Value: {first_value}
Last Value: {last_value}
Change: {change_pct:.1f}%
Direction: {direction}

Explain in {language}:
1. Why is this trend occurring?
2. What factors are driving this change?
3. Is this trend sustainable?

Respond with JSON:
{{
    "explanation": "Detailed explanation in {language}",
    "underlying_causes": ["cause1", "cause2"],
    "sustainability": "likely|unlikely|unclear",
    "key_observations": ["obs1", "obs2"]
}}
"""

        try:
            response = self.client.text_extract(
                text=f"Trend analysis for {metric_name}: {change_pct:.1f}% change",
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            return {
                'direction': direction,
                'strength': strength,
                'change_percentage': change_pct,
                'explanation': result.get('explanation', f'{direction} by {abs(change_pct):.1f}%'),
                'underlying_causes': result.get('underlying_causes', []),
                'sustainability': result.get('sustainability', 'unclear')
            }
        except Exception as e:
            logger.warning(f"Trend analysis failed: {str(e)}")
            return {
                'direction': direction,
                'strength': strength,
                'change_percentage': change_pct,
                'explanation': f'{direction} trend of {abs(change_pct):.1f}%'
            }

    def _explain_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_data: List[Dict[str, Any]],
        metric_name: str,
        language: str
    ) -> Dict[str, Any]:
        """Explain forecast results."""
        if not forecast_data or not historical_data:
            return {'summary': 'Insufficient data for forecast explanation'}

        hist_values = [d.get('value', 0) for d in historical_data[-10:]]  # Last 10 points
        forecast_values = [d.get('value', 0) for d in forecast_data]

        if not hist_values or not forecast_values:
            return {'summary': 'No numeric values in data'}

        last_historical = hist_values[-1]
        first_forecast = forecast_values[0]
        last_forecast = forecast_values[-1]

        change = last_forecast - last_historical
        change_pct = (change / abs(last_historical) * 100) if last_historical != 0 else 0

        prompt = f"""Explain this forecast for {metric_name} in {language}.

Historical Trend: Last 10 values show trend
Current Value: {last_historical}
Forecast Period: {len(forecast_data)} periods
Forecasted Final Value: {last_forecast}
Expected Change: {change_pct:.1f}%

Generate in {language}:
1. What does this forecast mean?
2. What is the business impact?
3. What should stakeholders expect?

Respond with JSON:
{{
    "summary": "1-2 sentence forecast summary in {language}",
    "detailed_explanation": "Paragraph explaining forecast implications",
    "business_impact": "Expected impact on business",
    "stakeholder_message": "Message for stakeholders",
    "confidence_level": 0.8
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{metric_name} forecast explanation",
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            return {
                'summary': result.get('summary', f'Forecast shows {change_pct:.1f}% change'),
                'detailed_explanation': result.get('detailed_explanation', ''),
                'business_impact': result.get('business_impact', ''),
                'expected_change': 'growth' if change_pct > 0 else 'decline' if change_pct < 0 else 'stable',
                'change_percentage': round(change_pct, 2),
                'confidence': result.get('confidence_level', 0.7)
            }
        except Exception as e:
            logger.warning(f"Forecast explanation failed: {str(e)}")
            return {
                'summary': f'Forecast shows {change_pct:.1f}% change in {metric_name}',
                'expected_change': 'growth' if change_pct > 0 else 'decline',
                'change_percentage': round(change_pct, 2)
            }

    def _identify_factors(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_data: List[Dict[str, Any]],
        metric_name: str,
        language: str
    ) -> List[Dict[str, str]]:
        """Identify key factors influencing forecast."""
        prompt = f"""Identify key factors influencing {metric_name} forecast.

Factors to consider:
- Seasonal patterns
- Economic indicators
- Industry trends
- Historical volatility
- External events

Respond with JSON:
{{
    "factors": [
        {{"factor": "factor name", "impact": "positive|negative|neutral", "magnitude": "high|medium|low"}},
        {{"factor": "seasonal demand", "impact": "positive", "magnitude": "high"}}
    ]
}}
"""

        try:
            response = self.client.text_extract(
                text=f"Factor identification for {metric_name}",
                prompt=prompt,
                model=self.model,
                temperature=0.3
            )

            result = self._parse_json_response(response)
            return result.get('factors', [])
        except Exception as e:
            logger.warning(f"Factor identification failed: {str(e)}")
            return []

    def _detect_turning_points(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect turning points in data."""
        turning_points = []

        # Check historical data for turning points
        values = [d.get('value', 0) for d in historical_data]
        if len(values) >= 3:
            for i in range(1, len(values) - 1):
                prev_change = values[i] - values[i - 1]
                next_change = values[i + 1] - values[i]
                
                if (prev_change > 0 and next_change < 0) or (prev_change < 0 and next_change > 0):
                    turning_points.append({
                        'type': 'historic',
                        'position': i,
                        'value': values[i],
                        'date': historical_data[i].get('date', 'unknown')
                    })

        # Check forecast for turning points
        forecast_values = [d.get('value', 0) for d in forecast_data]
        if len(forecast_values) >= 3:
            for i in range(1, len(forecast_values) - 1):
                prev_change = forecast_values[i] - forecast_values[i - 1]
                next_change = forecast_values[i + 1] - forecast_values[i]
                
                if (prev_change > 0 and next_change < 0) or (prev_change < 0 and next_change > 0):
                    turning_points.append({
                        'type': 'forecast',
                        'position': i,
                        'value': forecast_values[i],
                        'date': forecast_data[i].get('date', 'unknown'),
                        'significance': 'trend_change'
                    })

        return turning_points

    def _assess_forecast_risks(
        self,
        forecast_data: List[Dict[str, Any]],
        trend_analysis: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Assess risks in forecast."""
        prompt = f"""Assess risks in this forecast:

Trend: {trend_analysis.get('direction', 'unknown')}
Strength: {trend_analysis.get('strength', 0)}
Sustainability: {trend_analysis.get('sustainability', 'unclear')}

Identify potential risks in {language}:
1. Financial risks
2. Operational risks
3. Market risks
4. Assumption risks

Respond with JSON:
{{
    "risk_level": "low|medium|high|critical",
    "risks": [
        {{"risk": "description", "probability": "high|medium|low", "impact": "severe|moderate|minor"}}
    ],
    "mitigation_strategies": ["strategy1", "strategy2"]
}}
"""

        try:
            response = self.client.text_extract(
                text="Risk assessment for forecast",
                prompt=prompt,
                model=self.model,
                temperature=0.3
            )

            result = self._parse_json_response(response)
            return {
                'risk_level': result.get('risk_level', 'medium'),
                'indicators': result.get('risks', []),
                'mitigation_strategies': result.get('mitigation_strategies', [])
            }
        except Exception as e:
            logger.warning(f"Risk assessment failed: {str(e)}")
            return {
                'risk_level': 'medium',
                'indicators': [],
                'mitigation_strategies': []
            }

    def _generate_recommendations(
        self,
        trend_analysis: Dict[str, Any],
        forecast_explanation: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        language: str
    ) -> List[str]:
        """Generate actionable recommendations."""
        prompt = f"""Based on forecast analysis, generate recommendations in {language}:

Trend: {trend_analysis.get('direction', 'unknown')}
Risk Level: {risk_assessment.get('risk_level', 'medium')}
Expected Change: {forecast_explanation.get('expected_change', 'unknown')}

Provide 3-5 actionable recommendations in {language}.

Respond with JSON:
{{
    "recommendations": ["rec1", "rec2", "rec3"],
    "priority_actions": ["action1", "action2"]
}}
"""

        try:
            response = self.client.text_extract(
                text="Recommendation generation",
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            return result.get('recommendations', [])
        except Exception as e:
            logger.warning(f"Recommendation generation failed: {str(e)}")
            return []

    def _identify_affected_areas(self, metric_name: str) -> List[str]:
        """Identify business areas affected by forecast."""
        affected_areas_map = {
            'revenue': ['sales', 'cash_flow', 'profitability', 'growth'],
            'expenses': ['cash_flow', 'profitability', 'budget', 'cost_control'],
            'accounts_receivable': ['cash_flow', 'liquidity', 'working_capital'],
            'inventory': ['cash_flow', 'operations', 'profitability'],
            'vat': ['compliance', 'tax_filing', 'cash_flow', 'regulatory']
        }
        return affected_areas_map.get(metric_name.lower(), ['operations', 'financial'])

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                if end > start:
                    return json.loads(response[start:end].strip())
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                if end > start:
                    return json.loads(response[start:end].strip())
            logger.warning(f"Failed to parse forecast response: {response[:100]}")
            return {}
