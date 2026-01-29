import os
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from typing import Dict, Any, List
import json
import asyncio
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

class EmergentAIService:
    """Service for AI operations using Emergent LLM Key"""
    
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY', '')
    
    def process_document_with_vision(self, image_url: str, document_type: str = 'invoice') -> Dict[str, Any]:
        """Process document using AI vision capabilities"""
        try:
            # Create chat instance
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"doc_process_{document_type}",
                system_message="""You are an expert financial document processor specializing in Arabic and English documents. 
                Extract all text and structured data from the provided document. 
                Support both printed and handwritten text.
                Identify the language(s) used and extract financial data accurately.
                For invoices, extract: vendor name, customer name, invoice number, dates, amounts, tax, currency, and line items.
                Return results in JSON format with high accuracy."""
            ).with_model("openai", "gpt-4o")
            
            # Create message with image - use base64 encoding for simplicity
            # In production, you'd fetch and encode the image
            import base64
            import requests
            
            # Fetch image and convert to base64
            try:
                response = requests.get(image_url, timeout=30)
                image_base64 = base64.b64encode(response.content).decode('utf-8')
            except Exception as e:
                # Fallback: use placeholder or handle error
                return {
                    'success': False,
                    'error': f'Could not fetch image from URL: {str(e)}'
                }
            
            image_content = ImageContent(image_base64=image_base64)
            
            user_message = UserMessage(
                text=f"""Process this {document_type} document. Extract all text and structured financial data. 
                Identify if it's handwritten or printed, and the language(s) used (Arabic, English, or mixed).
                
                Return JSON with this exact structure:
                {{
                    "extractedText": {{"arabic": "", "english": "", "mixed": ""}},
                    "structuredData": {{
                        "vendorName": "",
                        "customerName": "",
                        "invoiceNumber": "",
                        "invoiceDate": "",
                        "dueDate": "",
                        "totalAmount": 0,
                        "taxAmount": 0,
                        "currency": "",
                        "items": []
                    }},
                    "confidence": 0,
                    "language": "en",
                    "isHandwritten": false
                }}""",
                file_contents=[image_content]
            )
            
            # Send message synchronously (we'll convert to async if needed)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text = loop.run_until_complete(chat.send_message(user_message))
            loop.close()
            
            # Parse response
            result = json.loads(response_text)
            
            return {
                'success': True,
                'extracted_text': result.get('extractedText', {}),
                'structured_data': result.get('structuredData', {}),
                'confidence': result.get('confidence', 0),
                'language': result.get('language', 'en'),
                'is_handwritten': result.get('isHandwritten', False)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_cash_flow_forecast(self, historical_data: List[Dict], periods: int = 6) -> List[Dict]:
        """Generate cash flow forecast using AI"""
        try:
            # Create chat instance
            chat = LlmChat(
                api_key=self.api_key,
                session_id="cash_flow_forecast",
                system_message="""You are a financial analyst AI specializing in cash flow forecasting. 
                Analyze historical transaction data and generate accurate cash flow predictions.
                Consider seasonal patterns, trends, and anomalies in the data.
                Provide confidence scores for each prediction."""
            ).with_model("openai", "gpt-4o")
            
            user_message = UserMessage(
                text=f"""Based on this historical financial data, generate a cash flow forecast for the next {periods} months:

{json.dumps(historical_data, default=str)}

Provide monthly predictions with inflow, outflow, net cash flow, and confidence scores.

Return JSON with this exact structure:
{{
    "forecasts": [
        {{
            "period": "2024-01",
            "predictedInflow": 0,
            "predictedOutflow": 0,
            "netCashFlow": 0,
            "confidence": 0
        }}
    ]
}}"""
            )
            
            # Send message synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text = loop.run_until_complete(chat.send_message(user_message))
            loop.close()
            
            # Parse response
            result = json.loads(response_text)
            return result.get('forecasts', [])
            
        except Exception as e:
            print(f"Forecast error: {str(e)}")
            return []
    
    def detect_anomalies(self, transactions: List[Dict]) -> List[Dict]:
        """Detect anomalies in financial transactions"""
        try:
            # Create chat instance
            chat = LlmChat(
                api_key=self.api_key,
                session_id="anomaly_detection",
                system_message="""You are a financial fraud detection and anomaly detection AI.
                Analyze transactions for unusual patterns, potential errors, or fraudulent activities.
                Consider amount deviations, frequency anomalies, duplicate transactions, and suspicious patterns.
                Classify anomalies by severity and provide actionable recommendations."""
            ).with_model("openai", "gpt-4o")
            
            user_message = UserMessage(
                text=f"""Analyze these transactions for anomalies:

{json.dumps(transactions, default=str)}

Identify any suspicious or unusual patterns.

Return JSON with this exact structure:
{{
    "anomalies": [
        {{
            "transactionId": "",
            "anomalyType": "",
            "severity": "low",
            "description": "",
            "recommendation": "",
            "confidence": 0
        }}
    ]
}}"""
            )
            
            # Send message synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text = loop.run_until_complete(chat.send_message(user_message))
            loop.close()
            
            # Parse response
            result = json.loads(response_text)
            return result.get('anomalies', [])
            
        except Exception as e:
            print(f"Anomaly detection error: {str(e)}")
            return []
    
    def analyze_trends(self, financial_data: List[Dict], metrics: List[str] = None) -> List[Dict]:
        """Analyze financial trends"""
        if metrics is None:
            metrics = ['revenue', 'expenses', 'profit']
        
        try:
            # Create chat instance
            chat = LlmChat(
                api_key=self.api_key,
                session_id="trend_analysis",
                system_message="""You are a financial trend analysis AI.
                Analyze financial data to identify trends, patterns, and insights.
                Calculate trend directions, percentage changes, and provide actionable insights."""
            ).with_model("openai", "gpt-4o")
            
            user_message = UserMessage(
                text=f"""Analyze trends for these metrics: {', '.join(metrics)}

Financial data:
{json.dumps(financial_data, default=str)}

Return JSON with this exact structure:
{{
    "trends": [
        {{
            "metric": "",
            "trend": "increasing",
            "changePercentage": 0,
            "insights": ""
        }}
    ]
}}"""
            )
            
            # Send message synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text = loop.run_until_complete(chat.send_message(user_message))
            loop.close()
            
            # Parse response
            result = json.loads(response_text)
            return result.get('trends', [])
            
        except Exception as e:
            print(f"Trend analysis error: {str(e)}")
            return []
    
    def generate_financial_insights(self, organization_data: Dict) -> List[str]:
        """Generate AI-powered financial insights"""
        try:
            # Create chat instance
            chat = LlmChat(
                api_key=self.api_key,
                session_id="financial_insights",
                system_message="""You are a senior financial advisor AI.
                Analyze comprehensive financial data and provide strategic insights.
                Focus on actionable recommendations for improving financial health."""
            ).with_model("openai", "gpt-4o")
            
            user_message = UserMessage(
                text=f"""Provide strategic financial insights based on this data:

{json.dumps(organization_data, default=str)}

Return JSON with this exact structure:
{{
    "insights": [
        "Insight 1",
        "Insight 2",
        "Insight 3"
    ]
}}"""
            )
            
            # Send message synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response_text = loop.run_until_complete(chat.send_message(user_message))
            loop.close()
            
            # Parse response
            result = json.loads(response_text)
            return result.get('insights', [])
            
        except Exception as e:
            print(f"Insights generation error: {str(e)}")
            return []

# Singleton instance
ai_service = EmergentAIService()
