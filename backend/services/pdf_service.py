from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib import colors
import uuid, os

def generate_dcf_report(valuation_data: dict) -> tuple:
    report_id = str(uuid.uuid4())
    
    # Use a project-local tmp directory for maximum portability
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tmp_dir = os.path.join(base_dir, "tmp")
    
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
                
    filepath = os.path.abspath(os.path.join(tmp_dir, f"rautrex_report_{report_id}.pdf"))
    
    doc = SimpleDocTemplate(filepath, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Header
    story.append(Paragraph("RAUTREX — DCF Valuation Report", styles['Title']))
    story.append(Paragraph(f"Ticker: {valuation_data.get('ticker', 'N/A')}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Key metrics table
    metrics = [
        ['Metric', 'Value'],
        ['Intrinsic Value', f"${valuation_data.get('intrinsic_value', 0):,.2f}"],
        ['Market Price', f"${valuation_data.get('market_price', 0):,.2f}"],
        ['Upside/Downside', f"{valuation_data.get('upside_pct', 0)*100:+.1f}%"],
        ['Enterprise Value', f"${valuation_data.get('enterprise_value', 0):,.0f}M"],
        ['WACC', f"{valuation_data.get('wacc', 0)*100:.1f}%"],
        ['Terminal Growth', f"{valuation_data.get('tgr', 0)*100:.1f}%"],
    ]
    
    t = Table(metrics, colWidths=[8*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0a0a0a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), 
            [colors.HexColor('#f5f5f5'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))
    
    # Sensitivity table
    if 'sensitivity_matrix' in valuation_data and valuation_data['sensitivity_matrix']:
        story.append(Paragraph("Sensitivity Analysis (Intrinsic Value per Share)", 
            styles['Heading2']))
        story.append(Spacer(1, 0.2*cm))
        
        st = Table(valuation_data['sensitivity_matrix'])
        st.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a1a1a')),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('TEXTCOLOR', (0,0), (0,-1), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        story.append(st)
    
    doc.build(story)
    return report_id, filepath
