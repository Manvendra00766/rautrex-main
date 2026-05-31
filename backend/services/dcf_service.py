import yfinance as yf
from typing import Optional
from schemas.dcf_schema import DCFInput, DCFOutput
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DCFService:
    @staticmethod
    def calculate_revenue_growth(revenue: list[float]) -> float:
        """CAGR formula: (last/first)^(1/(n-1)) - 1, capped at 30%"""
        if not revenue or len(revenue) < 2:
            return 0.05  # Default growth
        
        # We want the growth rate from the oldest to the newest in the provided list
        # Assuming list is chronological [Oldest -> Newest]
        n = len(revenue)
        first = revenue[0]
        last = revenue[-1]
        
        if first <= 0:
            return 0.05
            
        cagr = (last / first) ** (1 / (n - 1)) - 1
        # Cap projected growth rate at min(CAGR, 30%)
        capped_growth = max(-0.2, min(cagr, 0.3))
        print(f"[DCG] Calculated CAGR: {cagr:.4f}, Capped: {capped_growth:.4f}")
        return capped_growth

    @staticmethod
    def project_revenues(last_revenue: float, growth_rate: float, years: int) -> list[float]:
        """Compound each year forward"""
        projections = []
        current = last_revenue
        for _ in range(years):
            current *= (1 + growth_rate)
            projections.append(current)
        return projections

    @staticmethod
    def calculate_fcf(revenue: float, ebit_margin: float, tax_rate: float, capex_pct: float, da_pct: float, nwc_change_pct: float, year: int) -> float:
        """
        NOPAT = EBIT * (1 - tax_rate)
        FCF = NOPAT - CapEx + Depreciation - ΔNWC
        """
        ebit = revenue * ebit_margin
        nopat = ebit * (1 - tax_rate)
        capex = revenue * capex_pct
        da = revenue * da_pct
        nwc_change = revenue * nwc_change_pct
        
        fcf = nopat - capex + da - nwc_change
        
        print(f"  Year {year} | Revenue: {revenue:12.2f} | EBIT: {ebit:10.2f} | NOPAT: {nopat:10.2f} | CapEx: {capex:10.2f} | D&A: {da:10.2f} | dNWC: {nwc_change:10.2f} | FCF: {fcf:12.2f}")
        
        return fcf

    @staticmethod
    def discount_fcfs(fcfs: list[float], wacc: float) -> list[float]:
        """Each FCF / (1+wacc)^year"""
        return [fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcfs)]

    @staticmethod
    def calculate_terminal_value(last_fcf: float, tgr: float, wacc: float, num_years: int) -> float:
        """
        Gordon Growth: last_fcf * (1+tgr) / (wacc - tgr)
        Discount back to present: tv / (1+wacc)^num_years
        """
        if wacc <= tgr:
            # We'll handle this in the main loop or raise here
            raise ValueError(f"WACC ({wacc*100:.1f}%) must exceed Terminal Growth Rate ({tgr*100:.1f}%)")
        
        tv = (last_fcf * (1 + tgr)) / (wacc - tgr)
        return tv / ((1 + wacc) ** num_years)

    def fetch_current_price(self, ticker: str) -> Optional[float]:
        # Try Upstox API first for Indian assets via the pricing engine
        is_indian = ticker.endswith(".NS") or ticker.endswith(".BO") or "GS" in ticker or "GB" in ticker
        if is_indian:
            try:
                import asyncio
                from services.pricing_engine import get_batch_price_snapshots
                
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                price_map = loop.run_until_complete(get_batch_price_snapshots([ticker]))
                snap = price_map.get(ticker)
                if snap and snap.last_price > 0:
                    return float(snap.last_price)
            except Exception as upstox_err:
                logger.warning(f"[DCF] Upstox quote fetch failed for {ticker}: {upstox_err}. Falling back to yfinance.")

        stock = yf.Ticker(ticker)

        # Attempt 1: stock.info (comprehensive but slower, rate-limited)
        try:
            price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
            if price and float(price) > 0:
                return float(price)
        except Exception as e:
            logger.warning(f"[DCF] stock.info failed for {ticker}: {e}. Trying fast_info...")

        # Attempt 2: fast_info (direct API endpoint, more reliable under load)
        try:
            price = stock.fast_info.get('lastPrice')
            if price and float(price) > 0:
                return float(price)
        except Exception as e:
            logger.warning(f"[DCF] fast_info failed for {ticker}: {e}. Trying history...")

        # Attempt 3: last close from recent history (most reliable, always available)
        try:
            hist = stock.history(period='2d')
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"[DCF] All price fetch methods failed for {ticker}: {e}")

        return None

    def build_sensitivity_table(self, dcf_input: DCFInput) -> dict[str, dict[str, float]]:
        """
        Builds sensitivity table with full float precision.
        """
        wacc_range = [round(dcf_input.wacc + i, 3) for i in [-0.02, -0.01, 0, 0.01, 0.02]]
        tgr_range = [round(dcf_input.terminal_growth_rate + i, 3) for i in [-0.01, -0.005, 0, 0.005, 0.01]]
        
        table = {}
        growth_rate = self.calculate_revenue_growth(dcf_input.revenue)
        projected_revs = self.project_revenues(dcf_input.revenue[-1], growth_rate, dcf_input.projection_years)
        
        for w in wacc_range:
            w_key = f"{w*100:.1f}%"
            table[w_key] = {}
            for t in tgr_range:
                t_key = f"{t*100:.1f}%"
                
                if w <= t: 
                    table[w_key][t_key] = 0.0
                    continue
                
                # Recalculate FCFs for each cell to be absolutely sure no caching issues
                fcfs = [
                    self.calculate_fcf(rev, dcf_input.ebit_margin, dcf_input.tax_rate, dcf_input.capex_pct, dcf_input.da_pct, dcf_input.nwc_change_pct, i+1) 
                    for i, rev in enumerate(projected_revs)
                ]
                pv_fcfs = self.discount_fcfs(fcfs, w)
                pv_tv = self.calculate_terminal_value(fcfs[-1], t, w, dcf_input.projection_years)
                
                ev = sum(pv_fcfs) + pv_tv
                eq_val = ev - dcf_input.net_debt
                price = eq_val / dcf_input.shares_outstanding
                # Return full precision to frontend
                table[w_key][t_key] = float(price)
        
        return table

    def calculate_intrinsic_value(self, dcf_input: DCFInput) -> DCFOutput:
        print(f"\n[DCF] Starting valuation for {dcf_input.ticker}")
        
        warnings = list(dcf_input.warnings) if dcf_input.warnings else []
        errors = []
        
        # --- 0. Pre-Calculation Sanity Checks ---
        
        # WACC vs TGR Guard
        if dcf_input.wacc <= dcf_input.terminal_growth_rate:
            raise ValueError(f"WACC ({dcf_input.wacc*100:.1f}%) must exceed Terminal Growth Rate ({dcf_input.terminal_growth_rate*100:.1f}%)")

        # Revenue Sanity
        if any(r <= 0 for r in dcf_input.revenue):
            warnings.append("Unusual revenue pattern — verify source data")
            errors.append("Revenue values must be > 0")
            
        for i in range(1, len(dcf_input.revenue)):
            prev = dcf_input.revenue[i-1]
            curr = dcf_input.revenue[i]
            if prev > 0:
                growth = (curr - prev) / prev
                if growth < -0.5 or growth > 2.0:
                    if "Unusual revenue pattern — verify source data" not in warnings:
                        warnings.append("Unusual revenue pattern — verify source data")
        
        # Margin Sanity
        if dcf_input.ebit_margin < -0.5 or dcf_input.ebit_margin > 0.6:
            warnings.append("EBIT margin is outside typical range (-50% to +60%)")
        if dcf_input.ebit_margin < 0:
            warnings.append("Company has negative operating income")
            
        if dcf_input.tax_rate < 0 or dcf_input.tax_rate > 0.5:
            warnings.append("Tax rate is outside typical range (0% to 50%)")

        # --- 1. Growth Rate ---
        growth_rate = self.calculate_revenue_growth(dcf_input.revenue)
        
        # --- 2. Revenue Projections ---
        projected_revs = self.project_revenues(dcf_input.revenue[-1], growth_rate, dcf_input.projection_years)
        
        # --- 3. FCF Calculations ---
        print(f"[DCF] Projection Chain for {dcf_input.ticker}:")
        fcfs = [
            self.calculate_fcf(rev, dcf_input.ebit_margin, dcf_input.tax_rate, dcf_input.capex_pct, dcf_input.da_pct, dcf_input.nwc_change_pct, i+1) 
            for i, rev in enumerate(projected_revs)
        ]
        
        # FCF Sanity
        if all(f < 0 for f in fcfs):
            warnings.append("Negative FCF — DCF model unreliable for this company at current inputs")

        # --- 4. PV of FCFs ---
        pv_fcfs = self.discount_fcfs(fcfs, dcf_input.wacc)
        
        # --- 5. PV of Terminal Value ---
        pv_tv = self.calculate_terminal_value(fcfs[-1], dcf_input.terminal_growth_rate, dcf_input.wacc, dcf_input.projection_years)
        
        # --- 6. Enterprise & Equity Value ---
        enterprise_value = sum(pv_fcfs) + pv_tv
        
        # FCF Sanity (Terminal Value dependency)
        if enterprise_value > 0 and pv_tv / enterprise_value > 0.8:
            warnings.append("Heavy terminal value dependency — results sensitive to TGR assumption")
            
        equity_value = enterprise_value - dcf_input.net_debt
        
        intrinsic_price = 0.0
        if dcf_input.shares_outstanding > 0:
            intrinsic_price = equity_value / dcf_input.shares_outstanding
            
        # Valuation Sanity
        if intrinsic_price < 0:
            warnings.append("Negative equity value — company may be distressed or over-levered")

        print(f"[DCF] Equity Value: {equity_value:,.2f} | Shares: {dcf_input.shares_outstanding:,.2f} | Intrinsic Price: {intrinsic_price:,.2f}")

        # --- 7. Market Price and Upside ---
        current_price = self.fetch_current_price(dcf_input.ticker)
        if current_price is None:
            raise ValueError(f"Unable to fetch current price for {dcf_input.ticker}. DCF aborted.")
        
        upside = (intrinsic_price / current_price) - 1
        if intrinsic_price > 10 * current_price:
            warnings.append("Result >10x market price — check CapEx, D&A and NWC inputs")
                 
        # Calculate Data Quality Score
        score = "HIGH"
        num_warnings = len(warnings) + len(errors)
        if num_warnings >= 3:
            score = "LOW"
        elif num_warnings > 0:
            score = "MEDIUM"

        # --- 8. Sensitivity ---
        # Disable logging for sensitivity to avoid flooding logs
        import sys
        import os
        original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        try:
            sensitivity = self.build_sensitivity_table(dcf_input)
        finally:
            sys.stdout.close()
            sys.stdout = original_stdout
        
        return DCFOutput(
            ticker=dcf_input.ticker,
            intrinsic_value_per_share=round(intrinsic_price, 2),
            current_market_price=round(current_price, 2) if current_price else None,
            upside_downside_pct=round(upside, 4) if upside is not None else None,
            projected_fcfs=[round(f, 2) for f in fcfs],
            terminal_value=round(pv_tv * ((1 + dcf_input.wacc) ** dcf_input.projection_years), 2),
            enterprise_value=round(enterprise_value, 2),
            equity_value=round(equity_value, 2),
            wacc_used=dcf_input.wacc,
            sensitivity_table=sensitivity,
            valuation_date=datetime.now().strftime("%Y-%m-%d"),
            warnings=warnings,
            errors=errors,
            data_quality_score=score,
            field_sources=dcf_input.field_sources if dcf_input.field_sources else {},
            currency=dcf_input.currency,
            unit=dcf_input.unit,
            unit_label=dcf_input.unit_label,
            exchange=dcf_input.exchange,
            market_price_native=round(current_price, 2) if current_price else 0.0
        )

dcf_service = DCFService()
