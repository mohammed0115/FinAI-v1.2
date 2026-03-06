"""
Document Understanding AI Module

Provides semantic analysis, entity extraction, and structured financial information
extraction from documents using OpenAI's vision and language capabilities.

Features:
- Document type classification
- Entity extraction (vendors, invoices, VAT, line items)
- Semantic analysis and relationship extraction
- Document structure understanding
- Confidence scoring
- Bilingual (Arabic/English) support
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from core.ai.client import get_openai_client
from core.ai.errors import AIAPIError, ValidationError
from core.ai.utils import redact_sensitive_data

logger = logging.getLogger(__name__)


class DocumentUnderstanding:
    """
    Provides comprehensive document understanding including semantic analysis,
    entity extraction, and financial document classification.
    """

    def __init__(self):
        self.client = get_openai_client()
        self.model = 'gpt-4o-mini'

    def analyze_document(
        self,
        ocr_text: str,
        language: str = 'ar',
        document_type_hint: Optional[str] = None,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive document analysis combining classification,
        entity extraction, and semantic understanding.

        Args:
            ocr_text: Extracted text from document
            language: Document language ('ar', 'en', 'mixed')
            document_type_hint: Optional hint from file upload
            include_relationships: Whether to extract entity relationships

        Returns:
            Dict with:
            - document_type: Classification (invoice, receipt, etc.)
            - entities: Extracted entities with confidence
            - semantic_analysis: Key themes and relationships
            - summary: Document summary
            - financial_metrics: Key financial data
            - language_detected: Actual detected language
            - confidence: Overall confidence (0-1)
            - timestamp: Processing timestamp
        """
        try:
            start_time = datetime.utcnow()

            # Step 1: Classify document type
            doc_type_result = self._classify_document_type(
                ocr_text, language, document_type_hint
            )

            # Step 2: Extract entities based on document type
            entities_result = self._extract_entities(
                ocr_text, language, doc_type_result['document_type']
            )

            # Step 3: Semantic analysis
            semantic_result = self._perform_semantic_analysis(
                ocr_text, language, include_relationships
            )

            # Step 4: Financial metrics extraction
            financial_metrics = self._extract_financial_metrics(
                entities_result.get('entities', {}),
                ocr_text
            )

            # Combine results
            result = {
                'document_type': doc_type_result['document_type'],
                'document_type_confidence': doc_type_result['confidence'],
                'document_category': doc_type_result['category'],
                'entities': entities_result.get('entities', {}),
                'entity_relationships': semantic_result.get('relationships', []) if include_relationships else [],
                'semantic_themes': semantic_result.get('themes', []),
                'document_summary': semantic_result.get('summary', ''),
                'financial_metrics': financial_metrics,
                'key_findings': semantic_result.get('key_findings', []),
                'data_quality_assessment': self._assess_data_quality(entities_result),
                'language_detected': semantic_result.get('language', language),
                'overall_confidence': self._calculate_overall_confidence(
                    doc_type_result,
                    entities_result,
                    semantic_result
                ),
                'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000),
                'timestamp': start_time.isoformat()
            }

            logger.info(f"Document analysis completed: {result['document_type']}")
            return result

        except Exception as e:
            logger.error(f"Document understanding error: {str(e)}", exc_info=True)
            raise AIAPIError(f"Document analysis failed: {str(e)}")

    def _classify_document_type(
        self,
        text: str,
        language: str,
        hint: Optional[str]
    ) -> Dict[str, Any]:
        """Classify document type using AI."""
        classification_types = [
            'invoice', 'receipt', 'purchase_order', 'credit_memo',
            'debit_memo', 'bill_of_lading', 'packing_slip', 'contract'
        ]

        prompt = f"""Analyze the financial document and classify its type.

Document Types: {', '.join(classification_types)}

Document Text:
{redact_sensitive_data(text[:2000])}

Respond with JSON:
{{
    "document_type": "one of {classification_types}",
    "category": "expense|revenue|logistics|legal|other",
    "confidence": 0.95,
    "reasoning": "why this classification",
    "alternative_types": ["type1", "type2"]
}}
"""

        try:
            response = self.client.text_extract(
                text=text,
                prompt=prompt,
                model=self.model,
                temperature=0.2
            )

            result = self._parse_json_response(response)
            return {
                'document_type': result.get('document_type', 'unknown'),
                'category': result.get('category', 'other'),
                'confidence': result.get('confidence', 0.5),
                'alternative_types': result.get('alternative_types', [])
            }
        except Exception as e:
            logger.warning(f"Document classification failed: {str(e)}")
            return {
                'document_type': hint or 'unknown',
                'category': 'other',
                'confidence': 0.3,
                'alternative_types': []
            }

    def _extract_entities(
        self,
        text: str,
        language: str,
        doc_type: str
    ) -> Dict[str, Any]:
        """Extract financial entities from document."""
        entity_schema = {
            'vendor': ['name', 'vat_number', 'contact', 'address'],
            'customer': ['name', 'vat_number', 'contact', 'address'],
            'document': ['number', 'date', 'type', 'reference'],
            'financial': ['subtotal', 'tax', 'total', 'currency'],
            'items': [{'description': '', 'quantity': 0, 'unit_price': 0, 'tax_rate': 0}]
        }

        prompt = f"""Extract all financial entities from this {doc_type} document.

Required entities:
- Vendor/Supplier information (name, VAT, contact, address)
- Customer/Buyer information (name, VAT, contact, address)
- Document details (number, date, type, references)
- Financial totals (subtotal, tax amount, total, currency)
- Line items (description, quantity, unit price, tax applied)

Document:
{redact_sensitive_data(text[:3000])}

Respond with JSON containing only extracted data (nulls for missing):
{{
    "vendor": {{"name": null, "vat_number": null, "contact": null, "address": null}},
    "customer": {{"name": null, "vat_number": null, "contact": null, "address": null}},
    "document": {{"number": null, "date": null, "type": "{doc_type}", "reference": null}},
    "financial": {{"subtotal": null, "tax": null, "total": null, "currency": null}},
    "items": [],
    "extraction_confidence": 0.0,
    "missing_fields": []
}}
"""

        try:
            response = self.client.text_extract(
                text=text,
                prompt=prompt,
                model=self.model,
                temperature=0.1
            )

            result = self._parse_json_response(response)
            return {'entities': result}
        except Exception as e:
            logger.warning(f"Entity extraction failed: {str(e)}")
            return {'entities': {}}

    def _perform_semantic_analysis(
        self,
        text: str,
        language: str,
        include_relationships: bool
    ) -> Dict[str, Any]:
        """Perform semantic analysis and relationship extraction."""
        prompt = f"""Perform semantic analysis of this financial document.

Analyze:
1. Key themes and topics
2. Document summary in {language}
3. Important numeric relationships
4. Semantic entities and their relationships (if requested)
5. Detected language and text structure

Document (first 3000 chars):
{redact_sensitive_data(text[:3000])}

Respond with JSON:
{{
    "themes": ["theme1", "theme2"],
    "summary": "Brief document summary in {language}",
    "key_findings": ["finding1", "finding2"],
    "relationships": {{"entity1": {{"relates_to": "entity2", "relationship": "type"}}}},
    "language": "ar|en|mixed",
    "document_structure": "structured|semi-structured|unstructured",
    "text_complexity": "simple|moderate|complex"
}}
"""

        try:
            response = self.client.text_extract(
                text=text,
                prompt=prompt,
                model=self.model,
                temperature=0.3
            )

            result = self._parse_json_response(response)
            return result
        except Exception as e:
            logger.warning(f"Semantic analysis failed: {str(e)}")
            return {
                'themes': [],
                'summary': text[:200],
                'key_findings': [],
                'relationships': {},
                'language': language
            }

    def _extract_financial_metrics(
        self,
        entities: Dict[str, Any],
        full_text: str
    ) -> Dict[str, Any]:
        """Extract key financial metrics from entities and text."""
        try:
            financial = entities.get('financial', {})
            items = entities.get('items', [])

            metrics = {
                'total_amount': financial.get('total'),
                'tax_amount': financial.get('tax'),
                'subtotal': financial.get('subtotal'),
                'currency': financial.get('currency'),
                'line_item_count': len(items) if items else 0,
                'effective_tax_rate': None,
                'highest_unit_price': None,
                'lowest_unit_price': None,
                'total_quantity': None
            }

            # Calculate effective tax rate
            if financial.get('subtotal') and financial.get('tax'):
                try:
                    subtotal = float(financial['subtotal'])
                    tax = float(financial['tax'])
                    if subtotal > 0:
                        metrics['effective_tax_rate'] = round((tax / subtotal) * 100, 2)
                except (ValueError, TypeError):
                    pass

            # Analyze line items
            if items:
                unit_prices = []
                quantities = []
                for item in items:
                    try:
                        if isinstance(item, dict):
                            if 'unit_price' in item:
                                unit_prices.append(float(item['unit_price']))
                            if 'quantity' in item:
                                quantities.append(float(item['quantity']))
                    except (ValueError, TypeError):
                        pass

                if unit_prices:
                    metrics['highest_unit_price'] = max(unit_prices)
                    metrics['lowest_unit_price'] = min(unit_prices)
                if quantities:
                    metrics['total_quantity'] = sum(quantities)

            return metrics
        except Exception as e:
            logger.warning(f"Financial metrics extraction failed: {str(e)}")
            return {}

    def _assess_data_quality(
        self,
        entities_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess quality of extracted data."""
        entities = entities_result.get('entities', {})
        total_fields = 0
        populated_fields = 0

        for section_key, section_value in entities.items():
            if isinstance(section_value, dict):
                for field_key, field_value in section_value.items():
                    total_fields += 1
                    if field_value is not None and field_value != '':
                        populated_fields += 1
            elif isinstance(section_value, list):
                total_fields += len(section_value)
                populated_fields += sum(1 for item in section_value if item)

        completeness = populated_fields / total_fields if total_fields > 0 else 0

        return {
            'completeness_score': round(completeness * 100, 1),
            'total_fields_expected': total_fields,
            'populated_fields': populated_fields,
            'quality_level': 'high' if completeness >= 0.8 else 'medium' if completeness >= 0.5 else 'low',
            'missing_critical_fields': self._identify_missing_critical_fields(entities)
        }

    def _identify_missing_critical_fields(
        self,
        entities: Dict[str, Any]
    ) -> List[str]:
        """Identify missing critical financial fields."""
        critical_fields = {
            'vendor': ['name'],
            'document': ['number', 'date'],
            'financial': ['total']
        }

        missing = []
        for section, fields in critical_fields.items():
            section_data = entities.get(section, {})
            for field in fields:
                if field not in section_data or section_data[field] is None:
                    missing.append(f"{section}.{field}")

        return missing

    def _calculate_overall_confidence(
        self,
        doc_type_result: Dict[str, Any],
        entities_result: Dict[str, Any],
        semantic_result: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence score."""
        scores = [
            doc_type_result.get('confidence', 0.5),
            entities_result.get('entities', {}).get('extraction_confidence', 0.5),
            0.7  # Semantic analysis inherent confidence
        ]
        return round(sum(scores) / len(scores), 2)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response with error handling."""
        try:
            # Try direct parsing
            return json.loads(response)
        except json.JSONDecodeError:
            # Try extracting JSON from markdown code blocks
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

            logger.warning(f"Failed to parse response as JSON: {response[:100]}")
            return {}

    def detect_document_language(self, text: str) -> str:
        """Detect document language from text."""
        arabic_indicators = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        total_chars = len([c for c in text if c.isalpha()])

        if total_chars == 0:
            return 'unknown'

        arabic_ratio = arabic_indicators / total_chars
        if arabic_ratio > 0.7:
            return 'ar'
        elif arabic_ratio > 0.2:
            return 'mixed'
        else:
            return 'en'
