from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Line
from reportlab.graphics.charts.piecharts import Pie
import io
import matplotlib.pyplot as plt

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name='Section',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=16,
            textColor=colors.HexColor('#2E4057')
        ))
        self.styles.add(ParagraphStyle(
            name='Body',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=8
        ))

    def generate_report(self, data: dict) -> bytes:
        """Generate PDF report with cost breakdown"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch
        )
        elements = []

        # Add header
        self._add_header(elements)

        # Add design details
        self._add_design_details(elements, data)

        # Add production details
        self._add_production_details(elements, data)

        # Add cost breakdown
        self._add_cost_breakdown(elements, data)

        # Add complexity analysis
        if 'complexity_score' in data:
            self._add_complexity_analysis(elements, data)

        # Generate PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _add_header(self, elements):
        # Add title
        title_style = ParagraphStyle(
            'Title',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1A237E')
        )
        elements.append(Paragraph("Embroidery Cost Analysis", title_style))
        elements.append(Spacer(1, 20))

    def _add_design_details(self, elements, data):
        elements.append(Paragraph("Design Specifications", self.styles['Section']))

        # Create a table for design details
        design_data = [
            ['Dimension', 'Value'],
            ['Design Name', data.get('design_name', 'Untitled')],
            ['Width × Height', f"{data['width_mm']:.1f}mm × {data['height_mm']:.1f}mm"],
            ['Stitch Count', f"{data['stitch_count']:,}"],
            ['Thread Length', f"{data['thread_length_yards']:.1f} yards"],
            ['Color Changes', str(data.get('color_changes', 'N/A'))]
        ]

        table = Table(design_data, colWidths=[2*inch, 3*inch])
        table.setStyle(self._get_table_style())
        elements.append(table)
        elements.append(Spacer(1, 20))

    def _add_production_details(self, elements, data):
        elements.append(Paragraph("Production Information", self.styles['Section']))

        prod_data = [
            ['Parameter', 'Value'],
            ['Quantity', str(data['quantity'])],
            ['Active Heads', str(data.get('active_heads', 15))],
            ['Pieces per Cycle', str(data['pieces_per_cycle'])],
            ['Total Cycles', str(data['cycles'])],
            ['Time per Cycle', f"{data['time_per_cycle']:.1f} min"],
            ['Total Runtime', f"{data['total_runtime']:.1f} min"]
        ]

        if data.get('foam_used'):
            prod_data.extend([
                ['Foam Usage', 'Yes'],
                ['Foam Sheets', str(data.get('sheets_needed', 'N/A'))]
            ])

        table = Table(prod_data, colWidths=[2*inch, 3*inch])
        table.setStyle(self._get_table_style())
        elements.append(table)
        elements.append(Spacer(1, 20))

    def _add_cost_breakdown(self, elements, data):
        elements.append(Paragraph("Cost Breakdown", self.styles['Section']))

        costs_data = [
            ['Item', 'Quantity', 'Unit Cost', 'Total'],
            ['Thread', f"{data['total_spools']} spools", 
             f"${self._get_unit_cost(data['thread_cost'], data['total_spools']):.2f}",
             f"${data['thread_cost']:.2f}"],
            ['Bobbins', f"{data['total_bobbins']} pcs",
             f"${self._get_unit_cost(data['bobbin_cost'], data['total_bobbins']):.2f}",
             f"${data['bobbin_cost']:.2f}"]
        ]

        if data.get('foam_used'):
            costs_data.append([
                'Foam',
                f"{data['sheets_needed']} sheets",
                f"${data['foam_unit_cost']:.2f}",
                f"${data['total_cost']:.2f}"
            ])

        table = Table(costs_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(self._get_table_style(has_totals=True))
        elements.append(table)
        elements.append(Spacer(1, 20))

    def _add_complexity_analysis(self, elements, data):
        elements.append(Paragraph("Design Complexity Analysis", self.styles['Section']))

        complexity_data = [
            ['Metric', 'Score'],
            ['Overall Complexity', f"{data['complexity_score']:.1f}/100"],
            ['Direction Changes', str(data['direction_changes'])],
            ['Density Score', f"{data['density_score']:.1f}/10"],
            ['Stitch Length Variance', f"{data['stitch_length_variance']:.1f}/10"]
        ]

        table = Table(complexity_data, colWidths=[2*inch, 3*inch])
        table.setStyle(self._get_table_style())
        elements.append(table)

    def _get_table_style(self, has_totals=False):
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E3F2FD')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1A237E')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (-1, 1), (-1, -1), 'RIGHT')  # Right align numbers
        ]

        if has_totals:
            style.extend([
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F5F5F5')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
            ])

        return TableStyle(style)

    def _get_unit_cost(self, total_cost: float, quantity: int) -> float:
        """Calculate unit cost from total cost and quantity"""
        return total_cost / quantity if quantity > 0 else 0.0