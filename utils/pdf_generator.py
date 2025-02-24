from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name='Helvetica',
            fontName='Helvetica',
            fontSize=12,
            leading=14
        ))
        
    def generate_report(self, data: dict) -> bytes:
        """Generate PDF report with cost breakdown"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=24,
            spaceAfter=30
        )
        elements.append(Paragraph("Embroidery Cost Analysis", title_style))
        
        # Add design details
        self._add_design_details(elements, data)
        
        # Add cost breakdown
        self._add_cost_breakdown(elements, data)
        
        # Generate PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
        
    def _add_design_details(self, elements, data):
        """Add design specifications to PDF"""
        details_style = ParagraphStyle(
            'Details',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            spaceAfter=12
        )
        
        details = [
            f"Design Size: {data['width_mm']:.1f}mm x {data['height_mm']:.1f}mm",
            f"Stitch Count: {data['stitch_count']:,}",
            f"Thread Length: {data['thread_length_yards']:.1f} yards",
            f"Production Time: {data['runtime']:.1f} minutes"
        ]
        
        for detail in details:
            elements.append(Paragraph(detail, details_style))
        elements.append(Spacer(1, 20))
        
    def _add_cost_breakdown(self, elements, data):
        """Add cost breakdown table to PDF"""
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        
        table_data = [
            ['Item', 'Quantity', 'Unit Cost', 'Total'],
            ['Thread', f"{data['thread_spools']} spools", f"${data['thread_unit_cost']:.2f}", f"${data['thread_total']:.2f}"],
            ['Bobbins', f"{data['bobbins']} pcs", f"${data['bobbin_unit_cost']:.2f}", f"${data['bobbin_total']:.2f}"]
        ]
        
        if data.get('foam_used'):
            table_data.append(['Foam', f"{data['foam_sheets']} sheets", f"${data['foam_unit_cost']:.2f}", f"${data['foam_total']:.2f}"])
            
        table = Table(table_data)
        table.setStyle(table_style)
        elements.append(table)
