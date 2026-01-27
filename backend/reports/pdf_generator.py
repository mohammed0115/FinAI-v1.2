"""
Arabic PDF Audit Report Generator - مولد تقارير التدقيق بصيغة PDF بالعربية

SCOPE: READ-ONLY REPORT GENERATION
"""
import os
import io
import hashlib
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List
import logging

from django.conf import settings
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display

logger = logging.getLogger(__name__)

FONT_DIR = os.path.join(settings.BASE_DIR, 'static', 'fonts')
ARABIC_FONT_REGULAR = os.path.join(FONT_DIR, 'IBMPlexSansArabic-Regular.ttf')
ARABIC_FONT_BOLD = os.path.join(FONT_DIR, 'IBMPlexSansArabic-Bold.ttf')

def register_arabic_fonts():
    try:
        if os.path.exists(ARABIC_FONT_REGULAR):
            pdfmetrics.registerFont(TTFont('IBMPlexArabic', ARABIC_FONT_REGULAR))
        if os.path.exists(ARABIC_FONT_BOLD):
            pdfmetrics.registerFont(TTFont('IBMPlexArabic-Bold', ARABIC_FONT_BOLD))
    except Exception as e:
        logger.warning(f"Could not register Arabic fonts: {e}")

register_arabic_fonts()

def reshape_arabic(text):
    if not text:
        return ""
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except:
        return str(text)

class ArabicPDFAuditReportGenerator:
    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 2 * cm
        self._init_styles()
    
    def _init_styles(self):
        base = getSampleStyleSheet()
        self.styles = {
            'title': ParagraphStyle('Title', fontName='IBMPlexArabic-Bold', fontSize=24, alignment=TA_CENTER, spaceAfter=20),
            'subtitle': ParagraphStyle('Subtitle', fontName='IBMPlexArabic', fontSize=14, alignment=TA_CENTER, spaceAfter=10, textColor=colors.HexColor('#64748b')),
            'heading1': ParagraphStyle('H1', fontName='IBMPlexArabic-Bold', fontSize=16, alignment=TA_RIGHT, spaceBefore=20, spaceAfter=10),
            'heading2': ParagraphStyle('H2', fontName='IBMPlexArabic-Bold', fontSize=13, alignment=TA_RIGHT, spaceBefore=15, spaceAfter=8),
            'body': ParagraphStyle('Body', fontName='IBMPlexArabic', fontSize=10, alignment=TA_RIGHT, spaceBefore=4, spaceAfter=4, leading=16),
            'body_center': ParagraphStyle('BodyC', fontName='IBMPlexArabic', fontSize=10, alignment=TA_CENTER),
            'small': ParagraphStyle('Small', fontName='IBMPlexArabic', fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor('#6b7280')),
        }
    
    def generate_report(self, organization_data, compliance_data, findings_data, period_start, period_end, generated_by):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=self.margin, leftMargin=self.margin, topMargin=self.margin, bottomMargin=self.margin)
        story = []
        
        # Cover Page
        story.extend(self._build_cover(organization_data, period_start, period_end))
        story.append(PageBreak())
        
        # Executive Summary
        story.extend(self._build_summary(compliance_data, findings_data))
        story.append(PageBreak())
        
        # Compliance Scores
        story.extend(self._build_compliance(compliance_data))
        story.append(PageBreak())
        
        # Findings
        story.extend(self._build_findings(findings_data))
        story.append(PageBreak())
        
        # Evidence
        story.extend(self._build_evidence(organization_data, period_start, period_end, generated_by))
        
        # Disclaimer
        story.extend(self._build_disclaimer())
        
        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _build_cover(self, org, start, end):
        elements = [Spacer(1, 3*cm)]
        elements.append(Paragraph(reshape_arabic("تقرير التدقيق المالي"), self.styles['title']))
        elements.append(Paragraph("Financial Audit Report", self.styles['subtitle']))
        elements.append(Spacer(1, 1*cm))
        elements.append(HRFlowable(width="80%", thickness=2, color=colors.HexColor('#1e293b'), hAlign='CENTER'))
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(reshape_arabic(org.get('name', '')), self.styles['title']))
        if org.get('tax_id'):
            elements.append(Paragraph(reshape_arabic(f"الرقم الضريبي: {org['tax_id']}"), self.styles['body_center']))
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(reshape_arabic(f"فترة التدقيق: {start} - {end}"), self.styles['body_center']))
        elements.append(Spacer(1, 3*cm))
        elements.append(Paragraph(reshape_arabic(f"تاريخ الإنشاء: {timezone.now().strftime('%Y/%m/%d %H:%M')}"), self.styles['small']))
        elements.append(Paragraph(reshape_arabic("سري - للاستخدام الداخلي فقط"), self.styles['body_center']))
        return elements
    
    def _build_summary(self, compliance, findings):
        elements = []
        elements.append(Paragraph(reshape_arabic("الملخص التنفيذي"), self.styles['heading1']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        
        score = compliance.get('overall_score', 0)
        if score >= 80:
            text = "المنشأة تحقق مستوى جيد من الامتثال"
        elif score >= 60:
            text = "المنشأة تحتاج معالجة بعض أوجه القصور"
        else:
            text = "مخاطر امتثال كبيرة تتطلب إجراءات فورية"
        
        elements.append(Paragraph(reshape_arabic(text), self.styles['body']))
        elements.append(Spacer(1, 0.5*cm))
        
        critical = sum(1 for f in findings if f.get('risk_level') == 'critical')
        high = sum(1 for f in findings if f.get('risk_level') == 'high')
        impact = sum(Decimal(str(f.get('financial_impact', 0) or 0)) for f in findings)
        
        data = [
            [reshape_arabic("المؤشر"), reshape_arabic("القيمة")],
            [reshape_arabic("درجة الامتثال"), f"{score}%"],
            [reshape_arabic("إجمالي الملاحظات"), str(len(findings))],
            [reshape_arabic("ملاحظات حرجة"), str(critical)],
            [reshape_arabic("ملاحظات مرتفعة"), str(high)],
            [reshape_arabic("الأثر المالي"), f"{impact:,.2f} ر.س"],
        ]
        
        t = Table(data, colWidths=[8*cm, 6*cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'IBMPlexArabic'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0,0), (-1,0), 'IBMPlexArabic-Bold'),
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        elements.append(t)
        return elements
    
    def _build_compliance(self, compliance):
        elements = []
        elements.append(Paragraph(reshape_arabic("درجات الامتثال"), self.styles['heading1']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        
        scores = [
            ("ZATCA الفوترة الإلكترونية", compliance.get('zatca_score', 0)),
            ("ضريبة القيمة المضافة", compliance.get('vat_score', 0)),
            ("الزكاة", compliance.get('zakat_score', 0)),
        ]
        
        for name, score in scores:
            status = "ممتاز" if score >= 80 else ("يحتاج تحسين" if score >= 60 else "يحتاج معالجة")
            color = '#166534' if score >= 80 else ('#b45309' if score >= 60 else '#dc2626')
            
            elements.append(Paragraph(reshape_arabic(name), self.styles['heading2']))
            data = [[f"{score}%", reshape_arabic(status)]]
            t = Table(data, colWidths=[4*cm, 10*cm])
            t.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'IBMPlexArabic-Bold'),
                ('FONTSIZE', (0,0), (0,0), 20),
                ('TEXTCOLOR', (0,0), (0,0), colors.HexColor(color)),
                ('ALIGN', (0,0), (0,0), 'CENTER'),
                ('ALIGN', (1,0), (1,0), 'RIGHT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 0.3*cm))
        
        return elements
    
    def _build_findings(self, findings):
        elements = []
        elements.append(Paragraph(reshape_arabic("نتائج التدقيق"), self.styles['heading1']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        
        if not findings:
            elements.append(Paragraph(reshape_arabic("لا توجد نتائج تدقيق"), self.styles['body']))
            return elements
        
        risk_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_findings = sorted(findings, key=lambda x: risk_order.get(x.get('risk_level', 'low'), 4))
        
        for f in sorted_findings[:20]:  # Limit to 20
            risk = f.get('risk_level', 'low')
            risk_ar = {'critical': 'حرج', 'high': 'مرتفع', 'medium': 'متوسط', 'low': 'منخفض'}.get(risk, 'منخفض')
            bg = {'critical': '#fef2f2', 'high': '#fff7ed', 'medium': '#fefce8', 'low': '#f0fdf4'}.get(risk, '#f0fdf4')
            
            header = [[reshape_arabic(f"{f.get('finding_number', '')} - {f.get('title_ar', '')}"), reshape_arabic(risk_ar)]]
            ht = Table(header, colWidths=[12*cm, 2*cm])
            ht.setStyle(TableStyle([
                ('FONTNAME', (0,0), (-1,-1), 'IBMPlexArabic-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg)),
                ('ALIGN', (0,0), (0,0), 'RIGHT'),
                ('ALIGN', (1,0), (1,0), 'CENTER'),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
            ]))
            elements.append(ht)
            
            if f.get('description_ar'):
                elements.append(Paragraph(reshape_arabic(f"الوصف: {f['description_ar'][:200]}"), self.styles['small']))
            if f.get('ai_explanation_ar'):
                elements.append(Paragraph(reshape_arabic(f"تحليل AI: {f['ai_explanation_ar'][:150]}"), self.styles['small']))
            
            elements.append(Spacer(1, 0.4*cm))
        
        return elements
    
    def _build_evidence(self, org, start, end, generated_by):
        elements = []
        elements.append(Paragraph(reshape_arabic("أدلة التدقيق"), self.styles['heading1']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        
        ts = timezone.now()
        report_id = hashlib.sha256(f"{org.get('id', '')}{ts.isoformat()}".encode()).hexdigest()[:16].upper()
        
        data = [
            [reshape_arabic("البند"), reshape_arabic("القيمة")],
            [reshape_arabic("معرف التقرير"), f"RPT-{report_id}"],
            [reshape_arabic("المنشأة"), reshape_arabic(org.get('name', '-'))],
            [reshape_arabic("فترة التدقيق"), f"{start} - {end}"],
            [reshape_arabic("تاريخ الإنشاء"), ts.strftime('%Y/%m/%d %H:%M:%S')],
            [reshape_arabic("أنشئ بواسطة"), generated_by],
            [reshape_arabic("النظام"), "FinAI v4.0"],
        ]
        
        t = Table(data, colWidths=[5*cm, 9*cm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'IBMPlexArabic'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
            ('FONTNAME', (0,0), (-1,0), 'IBMPlexArabic-Bold'),
            ('ALIGN', (0,0), (0,-1), 'RIGHT'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t)
        return elements
    
    def _build_disclaimer(self):
        elements = [Spacer(1, 1*cm)]
        elements.append(Paragraph(reshape_arabic("إخلاء المسؤولية"), self.styles['heading1']))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        
        text = """هذا التقرير للقراءة فقط ولا يُعدّل أي بيانات. المعلومات مبنية على البيانات المتاحة وقت التحليل. 
لا يُعتبر رأياً قانونياً أو ضريبياً نهائياً. نظام FinAI هو نظام تدقيق ومراجعة وليس نظام فوترة إلكترونية."""
        
        elements.append(Paragraph(reshape_arabic(text), self.styles['body']))
        return elements
    
    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('IBMPlexArabic', 8)
        canvas.setFillColor(colors.HexColor('#9ca3af'))
        canvas.drawCentredString(self.page_width/2, 1.5*cm, reshape_arabic(f"صفحة {canvas.getPageNumber()}"))
        canvas.drawCentredString(self.page_width/2, 1*cm, reshape_arabic("FinAI - تقرير تدقيق للقراءة فقط"))
        canvas.restoreState()

arabic_pdf_generator = ArabicPDFAuditReportGenerator()
