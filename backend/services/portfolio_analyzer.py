from typing import List, Dict, Any, Optional
from core.logger import logger

def analyze_portfolio(holdings: List[Dict[str, Any]], onboarding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Analyzes imported broker portfolio data and generates insights.
    
    Holdings structure:
    {
        "ticker": str,
        "name": str,
        "asset_type": str,  # equity, mutual_fund, etf, gold, debt
        "sector": str,
        "market_cap_type": str,  # large, mid, small, micro
        "shares": float,
        "avg_cost": float,
        "current_price": float,
        "total_invested": float,
        "current_value": float,
        "pnl": float,
        "pnl_pct": float,
        "expense_ratio": float,  # for MFs/ETFs
        "category": str  # for MFs: equity, debt, hybrid, commodity
    }
    
    Onboarding data structure:
    {
        "investor_type": str,       # new, existing
        "risk_tolerance": str,      # safety, balanced, growth
        "horizon": str,             # under_1_year, 1-3 years, 3-7 years, 7_years_plus
        "goal": str,
        "monthly_amount": float
    }
    """
    try:
        if not holdings:
            return _get_empty_analysis_defaults(onboarding_data)

        # 1. Basic Aggregations
        total_invested = 0.0
        total_current_value = 0.0
        total_pnl = 0.0
        
        for h in holdings:
            total_invested += float(h.get("total_invested") or 0.0)
            total_current_value += float(h.get("current_value") or (float(h.get("shares") or 0.0) * float(h.get("current_price") or 0.0)))
        
        total_pnl = total_current_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100.0) if total_invested > 0 else 0.0

        # 2. Sector Concentration
        sector_values = {}
        for h in holdings:
            sec = h.get("sector") or "Unknown/Other"
            if h.get("asset_type") == "mutual_fund":
                # For mutual funds, we attribute sector based on fund category or mock diversified
                sec = "Diversified Mutual Fund"
            val = float(h.get("current_value") or 0.0)
            sector_values[sec] = sector_values.get(sec, 0.0) + val
            
        sector_concentration = {}
        sector_warnings = []
        for sec, val in sector_values.items():
            pct = (val / total_current_value * 100.0) if total_current_value > 0 else 0.0
            sector_concentration[sec] = {
                "value": round(val, 2),
                "pct": round(pct, 2)
            }
            if pct > 30.0 and sec != "Diversified Mutual Fund" and sec != "Unknown/Other":
                sector_warnings.append(
                    f"Over-concentration alert: {sec} makes up {pct:.1f}% of your portfolio (limit: 30%). Consider rebalancing."
                )

        # 3. Market Cap Distribution (for stocks and equity-based mutual funds)
        market_cap_values = {"large": 0.0, "mid": 0.0, "small": 0.0, "micro": 0.0, "unclassified": 0.0}
        for h in holdings:
            val = float(h.get("current_value") or 0.0)
            mc_type = str(h.get("market_cap_type") or "").lower()
            if mc_type in market_cap_values:
                market_cap_values[mc_type] += val
            else:
                # If mutual fund is large cap category, etc.
                category = str(h.get("category") or "").lower()
                name_lower = str(h.get("name") or "").lower()
                if "large cap" in name_lower or "bluechip" in name_lower:
                    market_cap_values["large"] += val
                elif "mid cap" in name_lower or "emerging" in name_lower:
                    market_cap_values["mid"] += val
                elif "small cap" in name_lower:
                    market_cap_values["small"] += val
                elif h.get("asset_type") == "equity":
                    market_cap_values["large"] += val  # Default stock fallback
                else:
                    market_cap_values["unclassified"] += val

        market_cap_pct = {}
        for mc_type, val in market_cap_values.items():
            pct = (val / total_current_value * 100.0) if total_current_value > 0 else 0.0
            market_cap_pct[mc_type] = {
                "value": round(val, 2),
                "pct": round(pct, 2)
            }

        # 4. Asset Type Distribution
        asset_values = {"equity": 0.0, "mutual_fund": 0.0, "etf": 0.0, "gold": 0.0, "debt": 0.0, "other": 0.0}
        for h in holdings:
            val = float(h.get("current_value") or 0.0)
            a_type = str(h.get("asset_type") or "").lower()
            if "gold" in a_type or "gold" in str(h.get("name") or "").lower():
                asset_values["gold"] += val
            elif a_type in asset_values:
                asset_values[a_type] += val
            else:
                asset_values["other"] += val

        asset_pct = {}
        for a_type, val in asset_values.items():
            pct = (val / total_current_value * 100.0) if total_current_value > 0 else 0.0
            asset_pct[a_type] = {
                "value": round(val, 2),
                "pct": round(pct, 2)
            }

        # 5. Diversification Score based on HHI (Herfindahl-Hirschman Index)
        # HHI = sum of squared weights. HHI range: 0 to 10,000 (10,000 = single holding).
        # Diversification score = 100 - (HHI / 100). Higher is more diversified.
        if len(holdings) > 0 and total_current_value > 0:
            hhi = sum(((float(h.get("current_value") or 0.0) / total_current_value * 100.0) ** 2) for h in holdings)
            # Cap HHI score dynamically
            diversification_score = max(10, min(98, round(100.0 - (hhi / 150.0))))
        else:
            diversification_score = 50

        # 6. Top Performers and Underperformers (P&L %)
        holdings_sorted = sorted(holdings, key=lambda x: float(x.get("pnl_pct") or 0.0), reverse=True)
        top_performers = []
        for h in holdings_sorted[:3]:
            if float(h.get("pnl_pct") or 0.0) > 0:
                top_performers.append({
                    "ticker": h.get("ticker") or h.get("name"),
                    "name": h.get("name"),
                    "pnl_pct": round(float(h.get("pnl_pct") or 0.0), 2),
                    "pnl": round(float(h.get("pnl") or 0.0), 2)
                })
        
        underperformers = []
        for h in reversed(holdings_sorted):
            if len(underperformers) >= 3:
                break
            underperformers.append({
                "ticker": h.get("ticker") or h.get("name"),
                "name": h.get("name"),
                "pnl_pct": round(float(h.get("pnl_pct") or 0.0), 2),
                "pnl": round(float(h.get("pnl") or 0.0), 2)
            })

        # 7. Overlap Detection (simulated overlap between mutual funds)
        overlap_results = []
        mfs = [h for h in holdings if h.get("asset_type") == "mutual_fund"]
        if len(mfs) >= 2:
            for i in range(len(mfs)):
                for j in range(i + 1, len(mfs)):
                    f1 = mfs[i]
                    f2 = mfs[j]
                    
                    # Compute a simulated overlap percentage based on fund names and categories
                    cat1 = str(f1.get("category") or "").lower()
                    cat2 = str(f2.get("category") or "").lower()
                    name1 = str(f1.get("name") or "").lower()
                    name2 = str(f2.get("name") or "").lower()
                    
                    overlap_pct = 5.0  # default base overlap
                    
                    if "index" in name1 and "index" in name2:
                        if "nifty 50" in name1 and "nifty 50" in name2:
                            overlap_pct = 95.0
                        elif "nifty" in name1 and "nifty" in name2:
                            overlap_pct = 80.0
                    elif "large cap" in name1 and "large cap" in name2:
                        overlap_pct = 65.0
                    elif "bluechip" in name1 and "bluechip" in name2:
                        overlap_pct = 60.0
                    elif "flexi cap" in name1 and "flexi cap" in name2:
                        overlap_pct = 45.0
                    elif ("large cap" in name1 or "bluechip" in name1) and ("flexi cap" in name2 or "large cap" in name2 or "bluechip" in name2):
                        overlap_pct = 35.0
                    elif cat1 == cat2 and cat1 == "equity":
                        overlap_pct = 25.0
                    elif cat1 != cat2:
                        overlap_pct = 8.0
                        
                    # Let's add simulated overlapping holdings
                    common_stocks = []
                    if overlap_pct > 30.0:
                        common_stocks = ["HDFC Bank", "Reliance Industries", "ICICI Bank"]
                    elif overlap_pct > 15.0:
                        common_stocks = ["Infosys", "ITC Ltd"]
                        
                    overlap_results.append({
                        "fund_a": f1.get("name"),
                        "fund_b": f2.get("name"),
                        "overlap_pct": round(overlap_pct, 1),
                        "common_holdings": common_stocks,
                        "risk_level": "High" if overlap_pct > 50.0 else "Medium" if overlap_pct > 25.0 else "Low"
                    })

        # 8. Risk Assessment based on actual portfolio allocation
        equity_weight = asset_pct.get("equity", {}).get("pct", 0.0) + asset_pct.get("mutual_fund", {}).get("pct", 0.0) * 0.8
        debt_weight = asset_pct.get("debt", {}).get("pct", 0.0) + asset_pct.get("mutual_fund", {}).get("pct", 0.0) * 0.15
        
        if equity_weight > 70.0:
            portfolio_risk = "Aggressive"
        elif equity_weight < 35.0:
            portfolio_risk = "Conservative"
        else:
            portfolio_risk = "Moderate"

        # 9. Fee Leakage Estimate
        annual_fee_leakage = 0.0
        mf_etf_value = 0.0
        for h in holdings:
            if h.get("asset_type") in ["mutual_fund", "etf"]:
                val = float(h.get("current_value") or 0.0)
                mf_etf_value += val
                exp_ratio = float(h.get("expense_ratio") or 0.0)
                annual_fee_leakage += val * (exp_ratio / 100.0)
                
        weighted_expense_ratio = (annual_fee_leakage / mf_etf_value * 100.0) if mf_etf_value > 0 else 0.0

        # 10. Gap Analysis: Compare actual vs ideal based on risk profile
        # Determine the user's target risk tolerance (from onboarding answers or default to actual portfolio risk)
        target_risk = "balanced"
        if onboarding_data:
            target_risk = str(onboarding_data.get("risk_tolerance") or "balanced").lower()
        else:
            target_risk = "balanced" if portfolio_risk == "Moderate" else "growth" if portfolio_risk == "Aggressive" else "safety"
            
        # Ideal Allocations in %: [Equity, Debt, Gold]
        if target_risk == "growth":
            ideal_equity, ideal_debt, ideal_gold = 75.0, 15.0, 10.0
        elif target_risk == "safety":
            ideal_equity, ideal_debt, ideal_gold = 20.0, 70.0, 10.0
        else: # balanced
            ideal_equity, ideal_debt, ideal_gold = 50.0, 30.0, 20.0

        # Compute current weights in %
        current_equity = asset_pct.get("equity", {}).get("pct", 0.0) + asset_pct.get("mutual_fund", {}).get("pct", 0.0)
        current_debt = asset_pct.get("debt", {}).get("pct", 0.0)
        current_gold = asset_pct.get("gold", {}).get("pct", 0.0) + asset_pct.get("etf", {}).get("pct", 0.0) # Assume ETF is gold-heavy mock or similar

        # Simple re-alignment to sum to 100
        total_standard = current_equity + current_debt + current_gold
        if total_standard > 0:
            current_equity = current_equity / total_standard * 100.0
            current_debt = current_debt / total_standard * 100.0
            current_gold = current_gold / total_standard * 100.0
        else:
            current_equity, current_debt, current_gold = 100.0, 0.0, 0.0

        gap_equity = current_equity - ideal_equity
        gap_debt = current_debt - ideal_debt
        gap_gold = current_gold - ideal_gold

        gap_analysis = {
            "target_risk_profile": target_risk.capitalize(),
            "actual": {
                "equity": round(current_equity, 1),
                "debt": round(current_debt, 1),
                "gold": round(current_gold, 1)
            },
            "ideal": {
                "equity": ideal_equity,
                "debt": ideal_debt,
                "gold": ideal_gold
            },
            "gaps": {
                "equity": round(gap_equity, 1),
                "debt": round(gap_debt, 1),
                "gold": round(gap_gold, 1)
            }
        }

        # 11. Actionable Recommendations
        recommendations = []
        
        # Recommendation 1: Fee Leakage
        if weighted_expense_ratio > 0.8:
            recommendations.append({
                "category": "Fees",
                "title": "High Expense Ratio Drag",
                "description": f"Your mutual funds have a high weighted expense ratio of {weighted_expense_ratio:.2f}%. Switching to 'Direct' plans instead of 'Regular' plans can save you around ₹{annual_fee_leakage * 0.01:,.0f} annually without changing your investments.",
                "action": "Switch to Direct Plans"
            })
        elif weighted_expense_ratio > 0:
            recommendations.append({
                "category": "Fees",
                "title": "Optimize Fund Fees",
                "description": f"You are paying ₹{annual_fee_leakage:,.0f} annually in mutual fund fees. Review low-cost index funds to reduce this fee drag.",
                "action": "View Index Fund Alternatives"
            })

        # Recommendation 2: Sector Concentration
        if sector_warnings:
            major_sector = max(sector_values, key=sector_values.get)
            recommendations.append({
                "category": "Diversification",
                "title": f"Heavy {major_sector} Allocation",
                "description": f"You are highly concentrated in the {major_sector} sector. Consider directing future SIPs towards other sectors like Banking, FMCG, or Pharma to build structural resilience.",
                "action": "Explore Other Sectors"
            })

        # Recommendation 3: Overlap
        high_overlaps = [o for o in overlap_results if o["overlap_pct"] > 40.0]
        if high_overlaps:
            o = high_overlaps[0]
            recommendations.append({
                "category": "Portfolio Overlap",
                "title": "Mutual Fund Overlap Detected",
                "description": f"'{o['fund_a']}' and '{o['fund_b']}' have a {o['overlap_pct']}% overlap. They both hold similar underlying stocks like {', '.join(o['common_holdings'][:2])}. Keeping both adds no diversification benefit.",
                "action": "Consolidate Mutual Funds"
            })

        # Recommendation 4: Asset Allocation Gaps
        if abs(gap_equity) > 15.0:
            direction = "under-allocated" if gap_equity < 0 else "over-allocated"
            recommendations.append({
                "category": "Asset Allocation",
                "title": f"Equity {direction.capitalize()}",
                "description": f"Your portfolio is {direction} in Equity by {abs(gap_equity):.1f}% compared to your ideal {ideal_equity}% target based on a {target_risk} risk tolerance. Consider rebalancing.",
                "action": "Rebalance Portfolio"
            })
            
        if abs(gap_gold) > 10.0 and gap_gold < 0:
            recommendations.append({
                "category": "Hedging",
                "title": "Missing Gold Protection",
                "description": "You are under-allocated in Gold/ETFs. Adding 10-15% gold allocation (e.g. via Sovereign Gold Bonds or Gold BeES) provides a strong buffer during market drawdowns.",
                "action": "Explore Gold ETFs"
            })

        # Final recommendations fallback
        if len(recommendations) < 3:
            recommendations.append({
                "category": "SIP",
                "title": "Establish Automated SIPs",
                "description": "Ensure your monthly surplus is systematically deployed using automated SIPs to benefit from rupee cost averaging.",
                "action": "Setup Automated SIP"
            })

        return {
            "total_invested": round(total_invested, 2),
            "current_value": round(total_current_value, 2),
            "overall_pnl": round(total_pnl, 2),
            "overall_pnl_pct": round(total_pnl_pct, 2),
            "diversification_score": diversification_score,
            "risk_assessment": portfolio_risk,
            "annual_fee_leakage": round(annual_fee_leakage, 2),
            "weighted_expense_ratio": round(weighted_expense_ratio, 2),
            "sector_concentration": sector_concentration,
            "sector_warnings": sector_warnings,
            "market_cap_distribution": market_cap_pct,
            "asset_type_distribution": asset_pct,
            "top_performers": top_performers,
            "underperformers": underperformers,
            "overlap_analysis": overlap_results,
            "gap_analysis": gap_analysis,
            "recommendations": recommendations[:4]
        }

    except Exception as e:
        logger.error(f"Error analyzing portfolio: {e}")
        return _get_empty_analysis_defaults(onboarding_data)

def _get_empty_analysis_defaults(onboarding_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    target_risk = "Balanced"
    if onboarding_data:
        target_risk = str(onboarding_data.get("risk_tolerance") or "balanced").capitalize()
        
    return {
        "total_invested": 0.0,
        "current_value": 0.0,
        "overall_pnl": 0.0,
        "overall_pnl_pct": 0.0,
        "diversification_score": 50,
        "risk_assessment": "Moderate",
        "annual_fee_leakage": 0.0,
        "weighted_expense_ratio": 0.0,
        "sector_concentration": {},
        "sector_warnings": [],
        "market_cap_distribution": {},
        "asset_type_distribution": {},
        "top_performers": [],
        "underperformers": [],
        "overlap_analysis": [],
        "gap_analysis": {
            "target_risk_profile": target_risk,
            "actual": {"equity": 0.0, "debt": 0.0, "gold": 0.0},
            "ideal": {"equity": 50.0, "debt": 30.0, "gold": 20.0},
            "gaps": {"equity": -50.0, "debt": -30.0, "gold": -20.0}
        },
        "recommendations": [
            {
                "category": "SIP",
                "title": "Start Systematic Investment Plan",
                "description": "Establish automated SIPs to begin building long-term wealth systematically.",
                "action": "Set up SIP"
            }
        ]
    }
