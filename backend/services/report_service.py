import io
import matplotlib
matplotlib.use('Agg') # Use non-GUI backend
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Dict, Any, Optional

from services.portfolio_engine import get_portfolio_overview
from services.risk_service import calculate_portfolio_risk
from supabase_client import supabase

# Rautrex Colors
BG_COLOR = colors.HexColor("#0f1117")
ACCENT_GREEN = colors.HexColor("#00ff88")
WHITE = colors.HexColor("#ffffff")

class ReportService:
    async def gather_report_data(self, portfolio_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        # 1. Portfolio Overview
        overview = await get_portfolio_overview(user_id, portfolio_id)
        
        if not overview.get("portfolio"):
            return None

        # 2. Risk Metrics
        positions_for_risk = [
            {"ticker": p["ticker"], "weight": p.get("weight_pct", 0)} 
            for p in overview["positions"]
        ]
        
        # Use last 1 year for risk if possible
        end_date = datetime.now()
        start_date = end_date - relativedelta(years=1)
        
        risk_data = {}
        if positions_for_risk:
            try:
                risk_data = await calculate_portfolio_risk(
                    positions_for_risk,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )
            except Exception as e:
                print(f"Risk calculation error in report: {e}")

        # 3. DCF Valuations
        dcf_valuations = []
        tickers = [p["ticker"] for p in overview["positions"]]
        if tickers:
            try:
                # Fetch latest saved DCF for each ticker in the portfolio
                # Using a subquery-like approach or just fetching all and filtering in Python
                response = supabase.table("dcf_valuations") \
                    .select("ticker, output_data, created_at") \
                    .eq("user_id", user_id) \
                    .in_("ticker", tickers) \
                    .order("created_at", desc=True) \
                    .execute()
                
                # Keep only the latest for each ticker
                seen_tickers = set()
                for row in response.data:
                    if row["ticker"] not in seen_tickers:
                        dcf_valuations.append({
                            "ticker": row["ticker"],
                            "intrinsic_value": row["output_data"].get("intrinsic_value_per_share"),
                            "current_price": row["output_data"].get("current_market_price"),
                            "upside": row["output_data"].get("upside_downside_pct")
                        })
                        seen_tickers.add(row["ticker"])
            except Exception as e:
                print(f"DCF fetch error in report: {e}")

        return {
            "overview": overview,
            "risk": risk_data,
            "dcf": dcf_valuations,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_name": "Rautrex User" # Ideally fetch from user profile
        }

    def generate_equity_chart(self, historical_equity: List[Dict[str, Any]]) -> io.BytesIO:
        if not historical_equity:
            return None
            
        dates = [datetime.strptime(row["snapshot_date"], "%Y-%m-%d") if isinstance(row["snapshot_date"], str) else row["snapshot_date"] for row in historical_equity]
        navs = [row["nav"] for row in historical_equity]
        
        plt.figure(figsize=(10, 5), facecolor='#0f1117')
        ax = plt.gca()
        ax.set_facecolor('#0f1117')
        
        plt.plot(dates, navs, color='#00ff88', linewidth=2)
        plt.fill_between(dates, navs, color='#00ff88', alpha=0.1)
        
        plt.title("Portfolio Performance (NAV)", color='white', fontsize=14, pad=20)
        plt.xlabel("Date", color='white')
        plt.ylabel("Net Asset Value ($)", color='white')
        
        ax.tick_params(axis='x', colors='white')
        ax.tick_params(axis='y', colors='white')
        for spine in ax.spines.values():
            spine.set_color('#2d3139')
            
        plt.grid(True, linestyle='--', alpha=0.1, color='white')
        plt.tight_layout()
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', facecolor='#0f1117')
        img_buffer.seek(0)
        plt.close()
        return img_buffer

    def build_pdf(self, data: Dict[str, Any]) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle(
            'RautrexTitle', parent=styles['Heading1'], 
            fontSize=32, textColor=ACCENT_GREEN, alignment=1, spaceAfter=20
        )
        subtitle_style = ParagraphStyle(
            'RautrexSubtitle', parent=styles['Normal'], 
            fontSize=16, textColor=WHITE, alignment=1, spaceAfter=50
        )
        section_style = ParagraphStyle(
            'RautrexSection', parent=styles['Heading2'], 
            fontSize=20, textColor=ACCENT_GREEN, spaceBefore=20, spaceAfter=10
        )
        normal_white = ParagraphStyle(
            'NormalWhite', parent=styles['Normal'], 
            fontSize=11, textColor=WHITE, leading=14
        )
        
        elements = []

        # --- PAGE 1: COVER ---
        elements.append(Spacer(1, 150))
        elements.append(Paragraph("RAUTREX", title_style))
        elements.append(Paragraph("Institutional Portfolio Report", subtitle_style))
        elements.append(Spacer(1, 50))
        elements.append(Paragraph(f"Portfolio: {data['overview']['portfolio']['name']}", subtitle_style))
        elements.append(Paragraph(f"Generated for: {data['user_name']}", normal_white))
        elements.append(Paragraph(f"Date: {data['generated_at']}", normal_white))
        elements.append(PageBreak())

        # --- PAGE 2: PORTFOLIO SUMMARY ---
        elements.append(Paragraph("Portfolio Summary", section_style))
        summary = data['overview']['summary']
        elements.append(Paragraph(f"Total NAV: ${summary['nav']:,.2f}", normal_white))
        elements.append(Paragraph(f"Cash Balance: ${summary['cash']:,.2f}", normal_white))
        elements.append(Paragraph(f"Holdings Count: {summary['holdings_count']}", normal_white))
        elements.append(Spacer(1, 20))
        
        # Holdings Table
        table_data = [["Symbol", "Shares", "Avg Cost", "Price", "P&L", "P&L%"]]
        for pos in data['overview']['positions']:
            table_data.append([
                pos['ticker'],
                f"{pos['shares']:.2f}",
                f"${pos['avg_cost_per_share']:,.2f}",
                f"${pos['live_price']:,.2f}",
                f"${pos['unrealized_pnl']:,.2f}",
                f"{pos['total_return_pct']:.2f}%"
            ])
            
        t = Table(table_data, colWidths=[80, 80, 80, 80, 80, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a1d26")),
            ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GREEN),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#0f1117")),
            ('TEXTCOLOR', (0, 1), (-1, -1), WHITE),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#2d3139")),
        ]))
        elements.append(t)
        elements.append(PageBreak())

        # --- PAGE 3: RISK ANALYTICS ---
        elements.append(Paragraph("Risk Analytics", section_style))
        risk = data.get('risk', {}).get('metrics', {})
        if risk:
            risk_metrics = [
                ["Metric", "Value", "Description"],
                ["VaR (95%)", f"{risk.get('var_95', 0)*100:.2f}%", "Max expected loss in 1 day with 95% confidence"],
                ["VaR (99%)", f"{risk.get('var_99', 0)*100:.2f}%", "Max expected loss in 1 day with 99% confidence"],
                ["Portfolio Beta", f"{risk.get('beta', 0):.2f}", "Sensitivity to benchmark (^GSPC)"],
                ["Sharpe Ratio", f"{risk.get('sharpe', 0):.2f}", "Risk-adjusted return vs 6.5% risk-free rate"],
                ["Max Drawdown", f"{risk.get('max_drawdown', 0)*100:.2f}%", "Peak-to-trough decline over 1 year"]
            ]
            rt = Table(risk_metrics, colWidths=[100, 80, 300])
            rt.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a1d26")),
                ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GREEN),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#2d3139")),
                ('TEXTCOLOR', (0, 1), (-1, -1), WHITE),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
            ]))
            elements.append(rt)
        else:
            elements.append(Paragraph("Risk data unavailable for this portfolio.", normal_white))
        elements.append(PageBreak())

        # --- PAGE 4: DCF VALUATIONS ---
        elements.append(Paragraph("DCF Valuations", section_style))
        elements.append(Paragraph("Valuations based on discounted cash flow projections (latest saved record per ticker).", normal_white))
        elements.append(Spacer(1, 20))
        
        dcf_table_data = [["Ticker", "Intrinsic Value", "Market Price", "Margin of Safety", "Verdict"]]
        if data.get('dcf'):
            for d in data['dcf']:
                upside = d.get('upside')
                mos = f"{upside*100:.1f}%" if upside is not None else "-"
                verdict = "Undervalued" if (upside or 0) > 0.2 else ("Overvalued" if (upside or 0) < -0.1 else "Fair Value")
                dcf_table_data.append([
                    d['ticker'],
                    f"${d.get('intrinsic_value', 0):,.2f}",
                    f"${d.get('current_price', 0):,.2f}",
                    mos,
                    verdict
                ])
        else:
            dcf_table_data.append(["-", "-", "-", "-", "No DCF data found"])
        
        dt = Table(dcf_table_data, colWidths=[80, 100, 100, 100, 100])
        dt.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1a1d26")),
            ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GREEN),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#2d3139")),
            ('TEXTCOLOR', (0, 1), (-1, -1), WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(dt)
        elements.append(PageBreak())

        # --- PAGE 5: PERFORMANCE CHART ---
        elements.append(Paragraph("Equity Growth Chart", section_style))
        chart_img = self.generate_equity_chart(data['overview']['equity_curve'])
        if chart_img:
            elements.append(Image(chart_img, width=500, height=250))
        else:
            elements.append(Paragraph("Insufficient history for chart generation.", normal_white))

        # Build PDF
        # To handle dark background, we need a custom Canvas handler or a full-page Rect.
        # Simplest: use a background Rect on every page.
        def add_background(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(BG_COLOR)
            canvas.rect(0, 0, A4[0], A4[1], fill=1)
            canvas.restoreState()

        doc.build(elements, onFirstPage=add_background, onLaterPages=add_background)
        buffer.seek(0)
        return buffer

report_service = ReportService()
