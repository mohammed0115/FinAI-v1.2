import io
import os
from typing import Any, List

from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import arabic_reshaper
from bidi.algorithm import get_display

from .report_presenter import build_report_presentation, format_amount


FONT_DIR = os.path.join(settings.BASE_DIR, 'static', 'fonts')
ARABIC_FONT_REGULAR = os.path.join(FONT_DIR, 'IBMPlexSansArabic-Regular.ttf')
ARABIC_FONT_BOLD = os.path.join(FONT_DIR, 'IBMPlexSansArabic-Bold.ttf')


def _register_fonts() -> None:
    try:
        if os.path.exists(ARABIC_FONT_REGULAR):
            pdfmetrics.registerFont(TTFont('IBMPlexArabic', ARABIC_FONT_REGULAR))
        if os.path.exists(ARABIC_FONT_BOLD):
            pdfmetrics.registerFont(TTFont('IBMPlexArabic-Bold', ARABIC_FONT_BOLD))
    except Exception:
        pass


_register_fonts()


def _shape_text(value: Any, lang: str) -> str:
    text = str(value or '')
    if lang != 'ar' or not text:
        return text
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


class InvoiceAuditPDFGenerator:
    def __init__(self) -> None:
        self.page_size = A4
        self.margin = 1.4 * cm
        self._init_styles()

    def _init_styles(self) -> None:
        sample = getSampleStyleSheet()
        self.styles = sample

        arabic_regular = 'IBMPlexArabic' if 'IBMPlexArabic' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
        arabic_bold = 'IBMPlexArabic-Bold' if 'IBMPlexArabic-Bold' in pdfmetrics.getRegisteredFontNames() else 'Helvetica-Bold'

        self.fonts = {
            'ar': {'regular': arabic_regular, 'bold': arabic_bold, 'align': TA_RIGHT},
            'en': {'regular': 'Helvetica', 'bold': 'Helvetica-Bold', 'align': TA_LEFT},
        }

    def _paragraph_style(self, name: str, lang: str, font_size: int, bold: bool = False, align: int | None = None) -> ParagraphStyle:
        font_family = self.fonts['ar' if lang == 'ar' else 'en']
        return ParagraphStyle(
            name=name,
            parent=self.styles['Normal'],
            fontName=font_family['bold' if bold else 'regular'],
            fontSize=font_size,
            leading=font_size + 4,
            alignment=font_family['align'] if align is None else align,
            spaceAfter=6,
            textColor=colors.HexColor('#0f172a'),
        )

    def _paragraph(self, text: Any, style: ParagraphStyle, lang: str) -> Paragraph:
        content = _shape_text(text, lang)
        content = content.replace('\n', '<br/>')
        return Paragraph(content, style)

    def _build_info_table(self, rows: List[List[Any]], lang: str, col_widths: List[float]) -> Table:
        label_style = self._paragraph_style('label', lang, 9, bold=True)
        value_style = self._paragraph_style('value', lang, 9)

        table_rows = []
        for left_value, right_value in rows:
            first = self._paragraph(left_value, label_style, lang)
            second = self._paragraph(right_value, value_style, lang)
            table_rows.append([first, second])

        table = Table(table_rows, colWidths=col_widths, hAlign='RIGHT' if lang == 'ar' else 'LEFT')
        table.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def generate(self, report, lang: str = 'ar') -> bytes:
        presentation = build_report_presentation(report, lang)
        labels = presentation['labels']
        buffer = io.BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
        )

        title_style = self._paragraph_style('title', lang, 18, bold=True, align=TA_CENTER)
        subtitle_style = self._paragraph_style('subtitle', lang, 10, align=TA_CENTER)
        heading_style = self._paragraph_style('heading', lang, 12, bold=True)
        body_style = self._paragraph_style('body', lang, 9)
        body_bold_style = self._paragraph_style('body_bold', lang, 9, bold=True)
        small_style = self._paragraph_style('small', lang, 8)

        story = [
            self._paragraph(labels['title'], title_style, lang),
            self._paragraph(labels['subtitle'], subtitle_style, lang),
            Spacer(1, 0.3 * cm),
        ]

        summary_rows = [
            [labels['report_number'], report.report_number],
            [labels['generated'], report.generated_at.strftime('%Y-%m-%d %H:%M') if report.generated_at else labels['no_data']],
            [labels['risk_level'], presentation['risk_level_label']],
            [labels['risk_score'], f'{report.risk_score}/100'],
        ]
        story.append(self._build_info_table(summary_rows, lang, [4.3 * cm, 11.3 * cm]))
        story.append(Spacer(1, 0.35 * cm))

        story.append(self._paragraph(labels['document_information'], heading_style, lang))
        document_rows = [
            [labels['document_id'], getattr(report.document, 'id', labels['no_data'])],
            [labels['file_name'], getattr(report.document, 'file_name', labels['no_data'])],
            [labels['upload_date'], report.upload_date.strftime('%Y-%m-%d %H:%M') if report.upload_date else labels['no_data']],
            [labels['ocr_engine'], report.ocr_engine or labels['no_data']],
            [labels['ocr_confidence'], f'{report.ocr_confidence_score or 0}%'],
            [labels['processing_status'], presentation['processing_status_label']],
        ]
        story.append(self._build_info_table(document_rows, lang, [4.3 * cm, 11.3 * cm]))
        story.append(Spacer(1, 0.35 * cm))

        story.append(self._paragraph(labels['invoice_information'], heading_style, lang))
        invoice_rows = [
            [labels['invoice_number'], report.extracted_invoice_number or labels['no_data']],
            [labels['issue_date'], report.extracted_issue_date.strftime('%Y-%m-%d') if report.extracted_issue_date else labels['no_data']],
            [labels['due_date'], report.extracted_due_date.strftime('%Y-%m-%d') if report.extracted_due_date else labels['no_data']],
            [labels['currency'], report.currency or labels['no_data']],
        ]
        story.append(self._build_info_table(invoice_rows, lang, [4.3 * cm, 11.3 * cm]))
        story.append(Spacer(1, 0.2 * cm))

        story.append(self._paragraph(labels['vendor_information'], body_bold_style, lang))
        story.append(
            self._build_info_table(
                [
                    [labels['name'], report.extracted_vendor_name or labels['no_data']],
                    [labels['address'], report.extracted_vendor_address or labels['no_data']],
                    [labels['tin'], report.extracted_vendor_tin or labels['no_data']],
                ],
                lang,
                [4.3 * cm, 11.3 * cm],
            )
        )
        story.append(Spacer(1, 0.2 * cm))

        story.append(self._paragraph(labels['customer_information'], body_bold_style, lang))
        story.append(
            self._build_info_table(
                [
                    [labels['name'], report.extracted_customer_name or labels['no_data']],
                    [labels['address'], report.extracted_customer_address or labels['no_data']],
                    [labels['tin'], report.extracted_customer_tin or labels['no_data']],
                ],
                lang,
                [4.3 * cm, 11.3 * cm],
            )
        )
        story.append(Spacer(1, 0.35 * cm))

        story.append(self._paragraph(labels['financial_totals'], heading_style, lang))
        total_rows = [
            [labels['subtotal'], f"{format_amount(report.subtotal_amount)} {report.currency or ''}".strip()],
            [labels['vat'], f"{format_amount(report.vat_amount)} {report.currency or ''}".strip()],
            [labels['total_amount'], f"{format_amount(report.total_amount)} {report.currency or ''}".strip()],
        ]
        story.append(self._build_info_table(total_rows, lang, [4.3 * cm, 11.3 * cm]))
        story.append(Spacer(1, 0.35 * cm))

        story.append(self._paragraph(labels['line_items'], heading_style, lang))
        if presentation['line_items']:
            header_style = self._paragraph_style('table_header', lang, 8, bold=True, align=TA_CENTER)
            cell_style = self._paragraph_style('table_cell', lang, 8)
            line_items_data = [
                [
                    self._paragraph(labels['description'], header_style, lang),
                    self._paragraph(labels['quantity'], header_style, lang),
                    self._paragraph(labels['unit_price'], header_style, lang),
                    self._paragraph(labels['discount'], header_style, lang),
                    self._paragraph(labels['total'], header_style, lang),
                ]
            ]
            for item in presentation['line_items']:
                line_items_data.append(
                    [
                        self._paragraph(item['description'], cell_style, lang),
                        self._paragraph(item['quantity'], cell_style, lang),
                        self._paragraph(item['unit_price'], cell_style, lang),
                        self._paragraph(item['discount'], cell_style, lang),
                        self._paragraph(item['total'], cell_style, lang),
                    ]
                )
            items_table = Table(line_items_data, colWidths=[7.3 * cm, 2.0 * cm, 2.3 * cm, 2.0 * cm, 2.4 * cm])
            items_table.setStyle(
                TableStyle(
                    [
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ]
                )
            )
            story.append(items_table)
        else:
            story.append(self._paragraph(labels['no_items'], body_style, lang))
        story.append(Spacer(1, 0.35 * cm))

        story.append(self._paragraph(labels['validation_checklist'], heading_style, lang))
        checklist_header = self._paragraph_style('checklist_header', lang, 8, bold=True, align=TA_CENTER)
        checklist_cell = self._paragraph_style('checklist_cell', lang, 8)
        checklist_data = [
            [
                self._paragraph(labels['check'], checklist_header, lang),
                self._paragraph(labels['checklist'], checklist_header, lang),
                self._paragraph(labels['status'], checklist_header, lang),
                self._paragraph(labels['notes'], checklist_header, lang),
            ]
        ]
        for row in presentation['checklist_rows']:
            notes_text = ' | '.join(row['notes']) if row['notes'] else labels['no_notes']
            checklist_data.append(
                [
                    self._paragraph(row['label'], checklist_cell, lang),
                    self._paragraph(row['completion_label'], checklist_cell, lang),
                    self._paragraph(row['status_label'], checklist_cell, lang),
                    self._paragraph(notes_text, checklist_cell, lang),
                ]
            )
        checklist_table = Table(checklist_data, colWidths=[4.2 * cm, 2.0 * cm, 3.0 * cm, 6.0 * cm])
        checklist_table.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]
            )
        )
        story.append(checklist_table)
        story.append(Spacer(1, 0.35 * cm))

        story.append(self._paragraph(labels['analysis_summary'], heading_style, lang))
        story.append(
            self._build_info_table(
                [
                    [labels['duplicate_detection'], f"{presentation['duplicate_status_label']} ({report.duplicate_score or 0}/100)"],
                    [labels['anomaly_detection'], f"{report.anomaly_score or 0}/100"],
                    [labels['risk_level'], presentation['risk_level_label']],
                ],
                lang,
                [4.3 * cm, 11.3 * cm],
            )
        )
        story.append(Spacer(1, 0.2 * cm))

        story.append(self._paragraph(labels['ai_analysis'], body_bold_style, lang))
        story.append(self._paragraph(presentation['ai_summary_display'], body_style, lang))
        story.append(self._paragraph(presentation['ai_findings_display'], body_style, lang))
        story.append(Spacer(1, 0.2 * cm))

        story.append(self._paragraph(labels['risk_factors'], body_bold_style, lang))
        if presentation['risk_factors']:
            story.append(self._paragraph(' • '.join(presentation['risk_factors']), small_style, lang))
        else:
            story.append(self._paragraph(labels['no_risk_factors'], small_style, lang))
        story.append(Spacer(1, 0.35 * cm))

        story.append(self._paragraph(labels['recommendation'], heading_style, lang))
        story.append(self._paragraph(presentation['recommendation_label'], body_bold_style, lang))
        story.append(self._paragraph(presentation['recommendation_reason_display'], body_style, lang))
        story.append(Spacer(1, 0.35 * cm))

        story.append(self._paragraph(labels['audit_trail'], heading_style, lang))
        if presentation['audit_trail']:
            trail_header = self._paragraph_style('trail_header', lang, 8, bold=True, align=TA_CENTER)
            trail_cell = self._paragraph_style('trail_cell', lang, 7)
            trail_data = [
                [
                    self._paragraph(labels['timestamp'], trail_header, lang),
                    self._paragraph(labels['event'], trail_header, lang),
                    self._paragraph(labels['status'], trail_header, lang),
                    self._paragraph(labels['details'], trail_header, lang),
                ]
            ]
            for entry in presentation['audit_trail']:
                trail_data.append(
                    [
                        self._paragraph(entry['timestamp'], trail_cell, lang),
                        self._paragraph(entry['event'], trail_cell, lang),
                        self._paragraph(entry['status'], trail_cell, lang),
                        self._paragraph(entry['details'], trail_cell, lang),
                    ]
                )
            trail_table = Table(trail_data, colWidths=[3.4 * cm, 4.1 * cm, 2.5 * cm, 6.2 * cm])
            trail_table.setStyle(
                TableStyle(
                    [
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ]
                )
            )
            story.append(trail_table)
        else:
            story.append(self._paragraph(labels['no_audit_events'], body_style, lang))

        document.build(story)
        buffer.seek(0)
        return buffer.getvalue()


invoice_audit_pdf_generator = InvoiceAuditPDFGenerator()
