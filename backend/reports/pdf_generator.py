"""
Arabic PDF Audit Report Generator - مولد تقارير التدقيق بصيغة PDF بالعربية

SCOPE: READ-ONLY REPORT GENERATION
This service generates immutable PDF audit reports from existing verified data.
It does NOT modify any audit logic, findings, or database records.

Features:
- Arabic RTL support with proper font embedding
- Cover page with organization details
- Executive summary
- Compliance scores (ZATCA, VAT, Zakat)
- Audit findings with Arabic AI explanations
- Regulatory references
- Recommendations
- Audit evidence with timestamps
"""
import os
import io
import hashlib
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging

from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display

logger = logging.getLogger(__name__)

# Font paths
FONT_DIR = os.path.join(settings.BASE_DIR, 'static', 'fonts')
ARABIC_FONT_REGULAR = os.path.join(FONT_DIR, 'IBMPlexSansArabic-Regular.ttf')
ARABIC_FONT_BOLD = os.path.join(FONT_DIR, 'IBMPlexSansArabic-Bold.ttf')


def register_arabic_fonts():
    """Register Arabic fonts with ReportLab"""
    try:
        if os.path.exists(ARABIC_FONT_REGULAR):
            pdfmetrics.registerFont(TTFont('IBMPlexArabic', ARABIC_FONT_REGULAR))
        if os.path.exists(ARABIC_FONT_BOLD):
            pdfmetrics.registerFont(TTFont('IBMPlexArabic-Bold', ARABIC_FONT_BOLD))
        logger.info("Arabic fonts registered successfully")
    except Exception as e:
        logger.warning(f"Could not register Arabic fonts: {e}")


# Register fonts on module load
register_arabic_fonts()


def reshape_arabic(text: str) -> str:
    """
    Reshape Arabic text for proper RTL rendering in PDF
    """
    if not text:
        return ""
    try:
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


class ArabicPDFStyles:
    """
    Arabic PDF Styles - أنماط PDF العربية
    Consistent styling for Arabic audit reports
    """
    
    @staticmethod
    def get_styles() -> Dict[str, ParagraphStyle]:
        """Get all paragraph styles for Arabic PDF"""
        base_styles = getSampleStyleSheet()
        
        return {
            'title': ParagraphStyle(
                'ArabicTitle',
                parent=base_styles['Title'],
                fontName='IBMPlexArabic-Bold',
                fontSize=24,
                alignment=TA_CENTER,
                spaceAfter=20,
                textColor=colors.HexColor('#1e293b'),
            ),
            'subtitle': ParagraphStyle(
                'ArabicSubtitle',
                parent=base_styles['Normal'],
                fontName='IBMPlexArabic',
                fontSize=14,
                alignment=TA_CENTER,
                spaceAfter=10,
                textColor=colors.HexColor('#64748b'),
            ),
            'heading1': ParagraphStyle(
                'ArabicH1',
                parent=base_styles['Heading1'],
                fontName='IBMPlexArabic-Bold',
                fontSize=16,
                alignment=TA_RIGHT,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor('#1e293b'),
                borderWidth=0,
                borderPadding=0,
                borderColor=colors.HexColor('#e2e8f0'),
            ),
            'heading2': ParagraphStyle(
                'ArabicH2',
                parent=base_styles['Heading2'],
                fontName='IBMPlexArabic-Bold',
                fontSize=13,
                alignment=TA_RIGHT,
                spaceBefore=15,
                spaceAfter=8,
                textColor=colors.HexColor('#334155'),
            ),
            'body': ParagraphStyle(
                'ArabicBody',
                parent=base_styles['Normal'],
                fontName='IBMPlexArabic',
                fontSize=10,
                alignment=TA_RIGHT,
                spaceBefore=4,
                spaceAfter=4,
                leading=16,
                textColor=colors.HexColor('#374151'),
            ),
            'body_center': ParagraphStyle(
                'ArabicBodyCenter',
                parent=base_styles['Normal'],
                fontName='IBMPlexArabic',
                fontSize=10,
                alignment=TA_CENTER,
                spaceBefore=4,
                spaceAfter=4,
                textColor=colors.HexColor('#374151'),
            ),
            'small': ParagraphStyle(
                'ArabicSmall',
                parent=base_styles['Normal'],
                fontName='IBMPlexArabic',
                fontSize=8,
                alignment=TA_RIGHT,
                textColor=colors.HexColor('#6b7280'),
            ),
            'footer': ParagraphStyle(
                'ArabicFooter',
                parent=base_styles['Normal'],
                fontName='IBMPlexArabic',
                fontSize=8,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#9ca3af'),
            ),
            'finding_critical': ParagraphStyle(
                'FindingCritical',
                parent=base_styles['Normal'],
                fontName='IBMPlexArabic-Bold',
                fontSize=10,
                alignment=TA_RIGHT,
                textColor=colors.HexColor('#991b1b'),
                backColor=colors.HexColor('#fef2f2'),
            ),
            'finding_high': ParagraphStyle(
                'FindingHigh',
                parent=base_styles['Normal'],
                fontName='IBMPlexArabic-Bold',
                fontSize=10,
                alignment=TA_RIGHT,
                textColor=colors.HexColor('#9a3412'),
                backColor=colors.HexColor('#fff7ed'),
            ),
            'score_good': ParagraphStyle(
                'ScoreGood',
                fontName='IBMPlexArabic-Bold',
                fontSize=24,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#166534'),
            ),
            'score_warning': ParagraphStyle(
                'ScoreWarning',
                fontName='IBMPlexArabic-Bold',
                fontSize=24,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#b45309'),
            ),
            'score_danger': ParagraphStyle(
                'ScoreDanger',
                fontName='IBMPlexArabic-Bold',
                fontSize=24,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#dc2626'),
            ),
        }


class ArabicPDFAuditReportGenerator:
    """
    مولد تقارير التدقيق بصيغة PDF بالعربية
    Arabic PDF Audit Report Generator
    
    READ-ONLY: Generates immutable PDF reports from existing verified data.
    Does NOT modify any audit logic, findings, or database records.
    """
    
    def __init__(self):
        self.styles = ArabicPDFStyles.get_styles()
        self.page_width, self.page_height = A4
        self.margin = 2 * cm
    
    def generate_report(
        self,
        organization_data: Dict,
        compliance_data: Dict,
        findings_data: List[Dict],
        period_start: date,
        period_end: date,
        generated_by: str,
    ) -> bytes:
        """
        Generate complete Arabic PDF audit report
        
        Returns: PDF file as bytes
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )
        
        # Build report content
        story = []
        
        # 1. Cover Page
        story.extend(self._build_cover_page(organization_data, period_start, period_end))
        story.append(PageBreak())
        
        # 2. Table of Contents
        story.extend(self._build_table_of_contents())
        story.append(PageBreak())
        
        # 3. Executive Summary
        story.extend(self._build_executive_summary(organization_data, compliance_data, findings_data))
        story.append(PageBreak())
        
        # 4. Compliance Scores
        story.extend(self._build_compliance_section(compliance_data))
        story.append(PageBreak())
        
        # 5. Audit Findings
        story.extend(self._build_findings_section(findings_data))
        story.append(PageBreak())
        
        # 6. Recommendations
        story.extend(self._build_recommendations_section(findings_data))
        story.append(PageBreak())
        
        # 7. Audit Evidence & Metadata
        story.extend(self._build_audit_evidence_section(
            organization_data, period_start, period_end, generated_by
        ))
        
        # 8. Disclaimer
        story.extend(self._build_disclaimer_section())
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_cover_page(
        self,
        organization_data: Dict,
        period_start: date,
        period_end: date
    ) -> List:
        """Build cover page"""
        elements = []
        
        # Add spacing from top
        elements.append(Spacer(1, 3 * cm))
        
        # Title
        elements.append(Paragraph(
            reshape_arabic("تقرير التدقيق المالي"),
            self.styles['title']
        ))
        
        elements.append(Paragraph(
            reshape_arabic("Financial Audit Report"),
            self.styles['subtitle']
        ))
        
        elements.append(Spacer(1, 1 * cm))
        
        # Horizontal line
        elements.append(HRFlowable(
            width="80%", thickness=2, color=colors.HexColor('#1e293b'),
            spaceBefore=10, spaceAfter=10, hAlign='CENTER'
        ))
        
        elements.append(Spacer(1, 1 * cm))
        
        # Organization name
        org_name = organization_data.get('name', 'المنشأة')
        elements.append(Paragraph(
            reshape_arabic(org_name),
            self.styles['title']
        ))
        
        elements.append(Spacer(1, 0.5 * cm))
        
        # Tax ID if available
        tax_id = organization_data.get('tax_id', '')
        if tax_id:
            elements.append(Paragraph(
                reshape_arabic(f"الرقم الضريبي: {tax_id}"),
                self.styles['body_center']
            ))
        
        elements.append(Spacer(1, 2 * cm))
        
        # Audit period
        period_text = f"فترة التدقيق: {period_start.strftime('%Y/%m/%d')} - {period_end.strftime('%Y/%m/%d')}"
        elements.append(Paragraph(
            reshape_arabic(period_text),
            self.styles['body_center']
        ))
        
        elements.append(Spacer(1, 3 * cm))
        
        # Generation date
        gen_date = timezone.now().strftime('%Y/%m/%d %H:%M')
        elements.append(Paragraph(
            reshape_arabic(f"تاريخ إنشاء التقرير: {gen_date}"),
            self.styles['small']
        ))
        
        elements.append(Spacer(1, 0.5 * cm))
        
        # Classification
        elements.append(Paragraph(
            reshape_arabic("سري - للاستخدام الداخلي فقط"),
            self.styles['body_center']
        ))
        
        return elements
    
    def _build_table_of_contents(self) -> List:
        """Build table of contents"""
        elements = []
        
        elements.append(Paragraph(
            reshape_arabic("المحتويات"),
            self.styles['heading1']
        ))
        
        elements.append(Spacer(1, 0.5 * cm))
        
        toc_items = [
            ("1. الملخص التنفيذي", "Executive Summary"),
            ("2. درجات الامتثال", "Compliance Scores"),
            ("3. نتائج التدقيق", "Audit Findings"),
            ("4. التوصيات", "Recommendations"),
            ("5. أدلة التدقيق", "Audit Evidence"),
            ("6. إخلاء المسؤولية", "Disclaimer"),
        ]
        
        for ar, en in toc_items:
            elements.append(Paragraph(
                reshape_arabic(ar),
                self.styles['body']
            ))
            elements.append(Spacer(1, 2 * mm))
        
        return elements
    
    def _build_executive_summary(
        self,
        organization_data: Dict,
        compliance_data: Dict,
        findings_data: List[Dict]
    ) -> List:
        """Build executive summary section"""
        elements = []
        
        elements.append(Paragraph(
            reshape_arabic("1. الملخص التنفيذي"),
            self.styles['heading1']
        ))
        
        elements.append(HRFlowable(
            width="100%", thickness=1, color=colors.HexColor('#e2e8f0'),
            spaceBefore=5, spaceAfter=10
        ))
        
        # Overall assessment
        overall_score = compliance_data.get('overall_score', 0)
        
        if overall_score >= 80:
            assessment_ar = "يُظهر التقييم الشامل أن المنشأة تحقق مستوى جيد من الامتثال للمتطلبات التنظيمية."
            risk_level = "منخفض"
        elif overall_score >= 60:
            assessment_ar = "يُظهر التقييم الشامل أن المنشأة تحتاج إلى معالجة بعض أوجه القصور في الامتثال."
            risk_level = "متوسط"
        else:
            assessment_ar = "يُظهر التقييم الشامل وجود مخاطر امتثال كبيرة تتطلب إجراءات تصحيحية فورية."
            risk_level = "مرتفع"
        
        elements.append(Paragraph(
            reshape_arabic(assessment_ar),
            self.styles['body']
        ))
        
        elements.append(Spacer(1, 0.5 * cm))
        
        # Key metrics table
        critical_count = sum(1 for f in findings_data if f.get('risk_level') == 'critical')
        high_count = sum(1 for f in findings_data if f.get('risk_level') == 'high')
        total_impact = sum(Decimal(str(f.get('financial_impact', 0) or 0)) for f in findings_data)
        
        metrics_data = [
            [reshape_arabic("المؤشر"), reshape_arabic("القيمة")],
            [reshape_arabic("درجة الامتثال الإجمالية"), f"{overall_score}%"],
            [reshape_arabic("مستوى المخاطر"), reshape_arabic(risk_level)],
            [reshape_arabic("إجمالي الملاحظات"), str(len(findings_data))],
            [reshape_arabic("ملاحظات حرجة"), str(critical_count)],
            [reshape_arabic("ملاحظات عالية الخطورة"), str(high_count)],
            [reshape_arabic("الأثر المالي المقدر"), f"{total_impact:,.2f} ر.س"],
        ]
        
        metrics_table = Table(metrics_data, colWidths=[8 * cm, 6 * cm])
        metrics_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'IBMPlexArabic'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'IBMPlexArabic-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(metrics_table)
        
        return elements
    
    def _build_compliance_section(self, compliance_data: Dict) -> List:
        """Build compliance scores section"""
        elements = []
        
        elements.append(Paragraph(
            reshape_arabic("2. درجات الامتثال"),
            self.styles['heading1']
        ))
        
        elements.append(HRFlowable(
            width="100%", thickness=1, color=colors.HexColor('#e2e8f0'),
            spaceBefore=5, spaceAfter=10
        ))
        
        # Score cards
        scores = [
            ("ZATCA الفوترة الإلكترونية", compliance_data.get('zatca_score', 0)),
            ("ضريبة القيمة المضافة", compliance_data.get('vat_score', 0)),
            ("الزكاة", compliance_data.get('zakat_score', 0)),
        ]
        
        for name, score in scores:
            elements.append(Paragraph(
                reshape_arabic(name),
                self.styles['heading2']
            ))
            
            # Score display
            if score >= 80:
                style = self.styles['score_good']
                status = "ممتاز"
            elif score >= 60:
                style = self.styles['score_warning']
                status = "يحتاج تحسين"
            else:
                style = self.styles['score_danger']
                status = "يحتاج معالجة"
            
            score_data = [
                [f"{score}%", reshape_arabic(status)]
            ]
            
            score_table = Table(score_data, colWidths=[4 * cm, 10 * cm])
            score_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, 0), 'IBMPlexArabic-Bold'),
                ('FONTNAME', (1, 0), (1, 0), 'IBMPlexArabic'),
                ('FONTSIZE', (0, 0), (0, 0), 20),
                ('FONTSIZE', (1, 0), (1, 0), 12),
                ('TEXTCOLOR', (0, 0), (0, 0), style.textColor),
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 10),
            ]))
            
            elements.append(score_table)
            elements.append(Spacer(1, 0.3 * cm))
        
        # VAT Summary if available
        vat_data = compliance_data.get('vat_summary', {})
        if vat_data:
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(Paragraph(
                reshape_arabic("ملخص ضريبة القيمة المضافة"),
                self.styles['heading2']
            ))
            
            vat_table_data = [
                [reshape_arabic("البند"), reshape_arabic("المبلغ (ر.س)")],
                [reshape_arabic("ض.ق.م المحصلة"), f"{vat_data.get('collected', 0):,.2f}"],
                [reshape_arabic("ض.ق.م المدفوعة"), f"{vat_data.get('paid', 0):,.2f}"],
                [reshape_arabic("صافي ض.ق.م"), f"{vat_data.get('net', 0):,.2f}"],
            ]
            
            vat_table = Table(vat_table_data, colWidths=[8 * cm, 6 * cm])
            vat_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'IBMPlexArabic'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('FONTNAME', (0, 0), (-1, 0), 'IBMPlexArabic-Bold'),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(vat_table)
        
        # Zakat Summary if available
        zakat_data = compliance_data.get('zakat_summary', {})
        if zakat_data:
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(Paragraph(
                reshape_arabic("ملخص الزكاة"),
                self.styles['heading2']
            ))
            
            zakat_table_data = [
                [reshape_arabic("البند"), reshape_arabic("المبلغ (ر.س)")],
                [reshape_arabic("الوعاء الزكوي"), f"{zakat_data.get('base', 0):,.2f}"],
                [reshape_arabic("الزكاة المستحقة"), f"{zakat_data.get('due', 0):,.2f}"],
            ]
            
            zakat_table = Table(zakat_table_data, colWidths=[8 * cm, 6 * cm])
            zakat_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'IBMPlexArabic'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('FONTNAME', (0, 0), (-1, 0), 'IBMPlexArabic-Bold'),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(zakat_table)
        
        return elements
    
    def _build_findings_section(self, findings_data: List[Dict]) -> List:
        """Build audit findings section"""
        elements = []
        
        elements.append(Paragraph(
            reshape_arabic("3. نتائج التدقيق"),
            self.styles['heading1']
        ))
        
        elements.append(HRFlowable(
            width="100%", thickness=1, color=colors.HexColor('#e2e8f0'),
            spaceBefore=5, spaceAfter=10
        ))
        
        if not findings_data:
            elements.append(Paragraph(
                reshape_arabic("لا توجد نتائج تدقيق في هذه الفترة."),
                self.styles['body']
            ))
            return elements
        
        # Summary by risk level
        risk_counts = {
            'critical': sum(1 for f in findings_data if f.get('risk_level') == 'critical'),
            'high': sum(1 for f in findings_data if f.get('risk_level') == 'high'),
            'medium': sum(1 for f in findings_data if f.get('risk_level') == 'medium'),
            'low': sum(1 for f in findings_data if f.get('risk_level') == 'low'),
        }
        
        summary_data = [
            [reshape_arabic("المستوى"), reshape_arabic("العدد")],
            [reshape_arabic("حرج"), str(risk_counts['critical'])],
            [reshape_arabic("مرتفع"), str(risk_counts['high'])],
            [reshape_arabic("متوسط"), str(risk_counts['medium'])],
            [reshape_arabic("منخفض"), str(risk_counts['low'])],
        ]
        
        summary_table = Table(summary_data, colWidths=[6 * cm, 4 * cm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'IBMPlexArabic'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'IBMPlexArabic-Bold'),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#fef2f2')),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fff7ed')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#fefce8')),
            ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#f0fdf4')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 1 * cm))
        
        # Individual findings
        elements.append(Paragraph(
            reshape_arabic("تفاصيل الملاحظات"),
            self.styles['heading2']
        ))
        
        # Sort by risk level
        risk_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_findings = sorted(findings_data, key=lambda x: risk_order.get(x.get('risk_level', 'low'), 4))
        
        for i, finding in enumerate(sorted_findings, 1):
            risk_level = finding.get('risk_level', 'low')
            risk_ar = {'critical': 'حرج', 'high': 'مرتفع', 'medium': 'متوسط', 'low': 'منخفض'}.get(risk_level, 'منخفض')
            
            # Risk level color
            if risk_level == 'critical':
                risk_color = colors.HexColor('#991b1b')
                bg_color = colors.HexColor('#fef2f2')
            elif risk_level == 'high':
                risk_color = colors.HexColor('#9a3412')
                bg_color = colors.HexColor('#fff7ed')
            elif risk_level == 'medium':
                risk_color = colors.HexColor('#854d0e')
                bg_color = colors.HexColor('#fefce8')
            else:
                risk_color = colors.HexColor('#166534')
                bg_color = colors.HexColor('#f0fdf4')
            
            # Finding header
            finding_number = finding.get('finding_number', f'F-{i:03d}')
            title_ar = finding.get('title_ar', 'ملاحظة تدقيق')
            
            header_data = [
                [
                    reshape_arabic(f"{finding_number} - {title_ar}"),
                    reshape_arabic(risk_ar)
                ]
            ]
            
            header_table = Table(header_data, colWidths=[12 * cm, 2 * cm])
            header_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'IBMPlexArabic-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (-1, -1), bg_color),
                ('TEXTCOLOR', (1, 0), (1, 0), risk_color),
                ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 8),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ]))
            
            elements.append(header_table)
            
            # Finding details
            details = []
            
            # Description
            desc = finding.get('description_ar', '')
            if desc:
                details.append([reshape_arabic("الوصف:"), reshape_arabic(desc[:200] + '...' if len(desc) > 200 else desc)])
            
            # Impact
            impact = finding.get('impact_ar', '')
            if impact:
                details.append([reshape_arabic("الأثر:"), reshape_arabic(impact[:150] + '...' if len(impact) > 150 else impact)])
            
            # Financial impact
            fin_impact = finding.get('financial_impact')
            if fin_impact:
                details.append([reshape_arabic("الأثر المالي:"), f"{Decimal(str(fin_impact)):,.2f} ر.س"])
            
            # AI Explanation
            ai_explanation = finding.get('ai_explanation_ar', '')
            if ai_explanation:
                details.append([reshape_arabic("تحليل الذكاء الاصطناعي:"), reshape_arabic(ai_explanation[:200] + '...' if len(ai_explanation) > 200 else ai_explanation)])
            
            # Regulatory reference
            reg_ref = finding.get('regulatory_reference', {})
            if reg_ref:
                ref_text = f"{reg_ref.get('article_number', '')} - {reg_ref.get('title_ar', '')}"
                details.append([reshape_arabic("المرجع التنظيمي:"), reshape_arabic(ref_text)])
            
            if details:
                details_table = Table(details, colWidths=[3.5 * cm, 10.5 * cm])
                details_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'IBMPlexArabic'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('FONTNAME', (0, 0), (0, -1), 'IBMPlexArabic-Bold'),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('PADDING', (0, 0), (-1, -1), 5),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ]))
                
                elements.append(details_table)
            
            elements.append(Spacer(1, 0.5 * cm))
        
        return elements
    
    def _build_recommendations_section(self, findings_data: List[Dict]) -> List:
        """Build recommendations section"""
        elements = []
        
        elements.append(Paragraph(
            reshape_arabic("4. التوصيات"),
            self.styles['heading1']
        ))
        
        elements.append(HRFlowable(
            width="100%", thickness=1, color=colors.HexColor('#e2e8f0'),
            spaceBefore=5, spaceAfter=10
        ))
        
        if not findings_data:
            elements.append(Paragraph(
                reshape_arabic("لا توجد توصيات في هذه الفترة."),
                self.styles['body']
            ))
            return elements
        
        # Extract recommendations from findings
        recommendations = []
        for finding in findings_data:
            rec = finding.get('recommendation_ar', '')
            if rec:
                recommendations.append({
                    'finding_number': finding.get('finding_number', ''),
                    'risk_level': finding.get('risk_level', 'low'),
                    'recommendation': rec,
                })
        
        # Sort by risk level
        risk_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: risk_order.get(x['risk_level'], 4))
        
        for i, rec in enumerate(recommendations, 1):
            risk_ar = {'critical': 'حرج', 'high': 'مرتفع', 'medium': 'متوسط', 'low': 'منخفض'}.get(rec['risk_level'], 'منخفض')
            
            elements.append(Paragraph(
                reshape_arabic(f"{i}. {rec['recommendation'][:300]}{'...' if len(rec['recommendation']) > 300 else ''}"),
                self.styles['body']
            ))
            elements.append(Paragraph(
                reshape_arabic(f"(المرجع: {rec['finding_number']} - أولوية: {risk_ar})"),
                self.styles['small']
            ))
            elements.append(Spacer(1, 0.3 * cm))
        
        return elements
    
    def _build_audit_evidence_section(
        self,
        organization_data: Dict,
        period_start: date,
        period_end: date,
        generated_by: str
    ) -> List:
        """Build audit evidence section"""
        elements = []
        
        elements.append(Paragraph(
            reshape_arabic("5. أدلة التدقيق"),
            self.styles['heading1']
        ))
        
        elements.append(HRFlowable(
            width="100%", thickness=1, color=colors.HexColor('#e2e8f0'),
            spaceBefore=5, spaceAfter=10
        ))
        
        # Generate report ID
        timestamp = timezone.now()
        report_id = hashlib.sha256(
            f"{organization_data.get('id', '')}{timestamp.isoformat()}{generated_by}".encode()
        ).hexdigest()[:16].upper()
        
        evidence_data = [
            [reshape_arabic("البند"), reshape_arabic("القيمة")],
            [reshape_arabic("معرف التقرير"), f"RPT-{report_id}"],
            [reshape_arabic("المنشأة"), reshape_arabic(organization_data.get('name', '-'))],
            [reshape_arabic("فترة التدقيق"), f"{period_start.strftime('%Y/%m/%d')} - {period_end.strftime('%Y/%m/%d')}"],
            [reshape_arabic("تاريخ الإنشاء"), timestamp.strftime('%Y/%m/%d %H:%M:%S')],
            [reshape_arabic("المنطقة الزمنية"), "UTC"],
            [reshape_arabic("أنشئ بواسطة"), generated_by],
            [reshape_arabic("النظام"), "FinAI v4.0"],
            [reshape_arabic("نوع التقرير"), reshape_arabic("تقرير تدقيق للقراءة فقط")],
        ]
        
        evidence_table = Table(evidence_data, colWidths=[5 * cm, 9 * cm])
        evidence_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'IBMPlexArabic'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0, 0), (-1, 0), 'IBMPlexArabic-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(evidence_table)
        
        elements.append(Spacer(1, 1 * cm))
        
        # Hash for integrity
        elements.append(Paragraph(
            reshape_arabic("تجزئة سلامة التقرير (SHA-256):"),
            self.styles['small']
        ))
        elements.append(Paragraph(
            report_id,
            self.styles['small']
        ))
        
        return elements
    
    def _build_disclaimer_section(self) -> List:
        """Build disclaimer section"""
        elements = []
        
        elements.append(Paragraph(
            reshape_arabic("6. إخلاء المسؤولية"),
            self.styles['heading1']
        ))
        
        elements.append(HRFlowable(
            width="100%", thickness=1, color=colors.HexColor('#e2e8f0'),
            spaceBefore=5, spaceAfter=10
        ))
        
        disclaimer_ar = """
هذا التقرير تم إنشاؤه بواسطة نظام FinAI للتدقيق المالي الذكي وهو مخصص للاستخدام الداخلي فقط.

• هذا التقرير هو تقرير للقراءة فقط ولا يُعدّل أي بيانات أو سجلات.
• المعلومات الواردة في هذا التقرير مبنية على البيانات المتاحة وقت التحليل.
• لا يُعتبر هذا التقرير رأياً قانونياً أو ضريبياً نهائياً.
• يجب مراجعة النتائج مع مستشار مالي أو قانوني مؤهل قبل اتخاذ أي قرارات.
• نظام FinAI هو نظام تدقيق ومراجعة وليس نظام فوترة إلكترونية.
• التحقق من ZATCA هو للمراجعة الداخلية فقط ولا يُغني عن التحقق الرسمي.

جميع الحقوق محفوظة © FinAI
        """
        
        elements.append(Paragraph(
            reshape_arabic(disclaimer_ar),
            self.styles['body']
        ))
        
        return elements
    
    def _add_header_footer(self, canvas, doc):
        """Add header and footer to each page"""
        canvas.saveState()
        
        # Footer
        canvas.setFont('IBMPlexArabic', 8)
        canvas.setFillColor(colors.HexColor('#9ca3af'))
        
        # Page number
        page_num = canvas.getPageNumber()
        footer_text = f"صفحة {page_num}"
        canvas.drawCentredString(self.page_width / 2, 1.5 * cm, reshape_arabic(footer_text))
        
        # System name
        canvas.drawCentredString(self.page_width / 2, 1 * cm, reshape_arabic("FinAI - تقرير تدقيق للقراءة فقط"))
        
        canvas.restoreState()


# Singleton instance
arabic_pdf_generator = ArabicPDFAuditReportGenerator()
