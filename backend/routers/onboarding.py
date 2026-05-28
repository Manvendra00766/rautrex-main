import os
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from core.logger import logger
from utils import safe_json
from auth import get_current_user
from services import db_service
from services.portfolio_analyzer import analyze_portfolio

router = APIRouter(tags=["Onboarding"])

# Pydantic schema for New Investor Flow
class NewInvestorOnboarding(BaseModel):
    goal: str = Field(..., description="Main reason to start investing")
    target: str = Field(..., description="What they are saving towards")
    horizon: str = Field(..., description="When they want to reach this goal")
    monthly_amount: str = Field(..., description="How much they can set aside monthly")
    risk_reaction: str = Field(..., description="Reaction to a 20% drop")
    risk_tolerance: str = Field(..., description="Safety vs Growth preference")
    knowledge_level: str = Field(..., description="Familiarity with mutual funds/SIPs")
    demat_holdings: Optional[List[Dict[str, Any]]] = Field(None, description="Imported demat holdings if connected")

# Pydantic schema for Existing Investor Flow
class ExistingInvestorOnboarding(BaseModel):
    asset_types: List[str] = Field(..., description="Where they are investing right now")
    portfolio_size: str = Field(..., description="Total portfolio worth today")
    experience_years: str = Field(..., description="How long they have been investing")
    goal_type: str = Field(..., description="Specific financial goal")
    monthly_contribution: str = Field(..., description="Monthly contribution amount")
    pain_point: str = Field(..., description="Biggest investment frustration")
    import_preference: str = Field(..., description="Preference for importing investments")
    demat_holdings: Optional[List[Dict[str, Any]]] = Field(None, description="Imported demat holdings if connected")

class DematSyncRequest(BaseModel):
    broker: str = Field(..., description="Broker brand name: zerodha, groww, or upstox")
    client_id: Optional[str] = Field(None, description="Client login ID")
    pin_or_otp: Optional[str] = Field(None, description="Secret security PIN or OTP")

class AnalyzePortfolioRequest(BaseModel):
    holdings: List[Dict[str, Any]] = Field(..., description="Holdings from broker sync")
    onboarding_data: Optional[Dict[str, Any]] = Field(None, description="Onboarding answers")


@router.post("/new")
async def onboarding_new_investor(data: NewInvestorOnboarding, current_user = Depends(get_current_user)):
    """
    Processes onboarding details for a new investor and returns a custom portfolio suggestion in rupees.
    """
    try:
        # 1. Parse/Standardize monthly amount in INR
        amount = 5000  # Default fallback
        if isinstance(data.monthly_amount, (int, float)):
            amount = int(data.monthly_amount)
        elif isinstance(data.monthly_amount, str):
            clean_str = data.monthly_amount.replace("₹", "").replace(",", "").strip()
            if "under" in clean_str.lower() or ("500" in clean_str and len(clean_str) < 10):
                amount = 500
            elif "500–2,000" in clean_str or "500-2,000" in clean_str or "500–2000" in clean_str or "500-2000" in clean_str:
                amount = 1000
            elif "2,000–5,000" in clean_str or "2,000-5,000" in clean_str or "2000–5000" in clean_str or "2000-5000" in clean_str:
                amount = 3500
            elif "5,000–15,000" in clean_str or "5,000-15,000" in clean_str or "5000–15000" in clean_str or "5000-15000" in clean_str:
                amount = 10000
            elif "15,000+" in clean_str or "15000+" in clean_str:
                amount = 20000
            else:
                import re
                nums = re.findall(r'\d+', clean_str)
                if nums:
                    amount = int(nums[0])
                    
        # 2. Normalize other inputs to standard keys
        tolerance = "balanced"
        if "safety" in data.risk_tolerance.lower() or "yes" in data.risk_tolerance.lower():
            tolerance = "safety"
        elif "growth" in data.risk_tolerance.lower() or "no" in data.risk_tolerance.lower():
            tolerance = "growth"
        elif "balanced" in data.risk_tolerance.lower() or "maybe" in data.risk_tolerance.lower():
            tolerance = "balanced"
            
        reaction = "wait"
        if "pull" in data.risk_reaction.lower():
            reaction = "pullout"
        elif "worry" in data.risk_reaction.lower() or "wait" in data.risk_reaction.lower():
            reaction = "wait"
        elif "calm" in data.risk_reaction.lower():
            reaction = "calm"
        elif "invest more" in data.risk_reaction.lower() or "cheap" in data.risk_reaction.lower() or "buymore" in data.risk_reaction.lower():
            reaction = "buymore"

        horizon = "1-3 years"
        if "1 year" in data.horizon.lower() or "under" in data.horizon.lower() or "within" in data.horizon.lower():
            horizon = "under_1_year"
        elif "1–3" in data.horizon or "1-3" in data.horizon:
            horizon = "1-3 years"
        elif "3–7" in data.horizon or "3-7" in data.horizon:
            horizon = "3-7 years"
        elif "7+" in data.horizon or "long term" in data.horizon.lower() or "no rush" in data.horizon.lower():
            horizon = "7_years_plus"

        # 3. Determine risk profile base weight allocation
        if reaction == "pullout" or tolerance == "safety":
            profile = "Conservative"
            equity, debt, gold = 20, 70, 10
        elif reaction in ("calm", "buymore") and tolerance == "growth":
            profile = "Aggressive"
            equity, debt, gold = 75, 15, 10
        else:
            profile = "Moderate"
            equity, debt, gold = 50, 30, 20

        # 4. Adjust for time horizon
        if horizon == "under_1_year":
            shift = min(20, equity)
            equity -= shift
            debt += shift
        elif horizon == "3-7 years":
            shift = min(10, debt)
            debt -= shift
            equity += shift
        elif horizon == "7_years_plus":
            shift = min(20, debt)
            debt -= shift
            equity += shift
            remaining_shift = 20 - shift
            if remaining_shift > 0:
                gold_shift = min(remaining_shift, gold)
                gold -= gold_shift
                equity += gold_shift

        # 5. Calculate Rupee amounts & round to nearest ₹100
        eq_rupees = round((amount * equity / 100) / 100) * 100
        db_rupees = round((amount * debt / 100) / 100) * 100
        gd_rupees = round((amount * gold / 100) / 100) * 100

        # Adjust any rounding residual differences against the largest category
        current_sum = eq_rupees + db_rupees + gd_rupees
        diff = amount - current_sum
        if diff != 0:
            cats = [("equity", eq_rupees), ("gold", gd_rupees), ("debt", db_rupees)]
            cats.sort(key=lambda x: x[1], reverse=True)
            largest_cat = cats[0][0]
            if largest_cat == "equity":
                eq_rupees += diff
            elif largest_cat == "gold":
                gd_rupees += diff
            else:
                db_rupees += diff

        # 6. Apply Minimum ₹500 rule (Move to next category: Equity -> Gold -> Debt -> Equity)
        for _ in range(3):
            if 0 < eq_rupees < 500:
                gd_rupees += eq_rupees
                eq_rupees = 0
            if 0 < gd_rupees < 500:
                db_rupees += gd_rupees
                gd_rupees = 0
            if 0 < db_rupees < 500:
                eq_rupees += db_rupees
                db_rupees = 0

        # Re-ensure exact sum fits the total budget after merging
        current_sum = eq_rupees + db_rupees + gd_rupees
        diff = amount - current_sum
        if diff != 0:
            cats = [("equity", eq_rupees), ("gold", gd_rupees), ("debt", db_rupees)]
            cats.sort(key=lambda x: x[1], reverse=True)
            largest_cat = cats[0][0]
            if largest_cat == "equity":
                eq_rupees += diff
            elif largest_cat == "gold":
                gd_rupees += diff
            else:
                db_rupees += diff

        # 7. Formulate output allocations
        allocations = []
        if eq_rupees >= 500:
            allocations.append({
                "category": "Large cap mutual fund",
                "amount": eq_rupees,
                "example_fund": "Mirae Asset Large Cap Fund",
                "where_to_buy": "Groww or Zerodha Coin",
                "why": "Safe, steady growth from top 100 companies"
            })
        if gd_rupees >= 500:
            allocations.append({
                "category": "Gold ETF",
                "amount": gd_rupees,
                "example_fund": "Nippon India Gold ETF",
                "where_to_buy": "Zerodha Kite",
                "why": "Protects your money when markets fall"
            })
        if db_rupees >= 500:
            allocations.append({
                "category": "Liquid fund",
                "amount": db_rupees,
                "example_fund": "Parag Parikh Liquid Fund",
                "where_to_buy": "Groww",
                "why": "Like a savings account but with better returns"
            })

        # 8. Dynamic copywriting for plain_summary
        summary_parts = []
        for alloc in allocations:
            cat_name = alloc['category'].lower()
            if "large cap" in cat_name:
                cat_name = "large cap fund"
            elif "gold" in cat_name:
                cat_name = "gold"
            elif "liquid" in cat_name:
                cat_name = "liquid fund"
            summary_parts.append(f"₹{alloc['amount']:,} in a {cat_name}")
            
        if len(summary_parts) > 1:
            plain_summary = "Every month, put " + ", ".join(summary_parts[:-1]) + f", and {summary_parts[-1]}."
        elif len(summary_parts) == 1:
            plain_summary = f"Every month, put {summary_parts[0]}."
        else:
            plain_summary = "No allocations generated."
        plain_summary += " That's it."

        result = {
            "portfolio_suggestion": {
                "allocations": allocations,
                "total": amount,
                "plain_summary": plain_summary,
                "first_step": "Open Groww first — it takes 10 minutes and you can start with ₹500."
            }
        }
        
        # 9. Build and save custom strategy/portfolio inside the DB for the user
        try:
            portfolio_name = "Rautrex " + ("Wealth Accelerator" if profile == "Aggressive" else "Capital Shield" if profile == "Conservative" else "Core Growth") + " Plan"
            description_text = f"Customised SIP Strategy for saving towards '{data.target}'. {plain_summary}"
            await db_service.create_portfolio(
                user_id=current_user.id,
                name=portfolio_name,
                strategy=profile,
                cash_balance=float(amount),
                description=description_text
            )
            logger.info(f"Successfully saved customized onboarding strategy portfolio in DB for user {current_user.id}")
        except Exception as db_err:
            logger.error(f"Failed to save customized strategy portfolio in DB: {db_err}")
            
        # 10. Check if demat holdings are provided for analysis
        if data.demat_holdings:
            onboarding_context = {
                "investor_type": "new",
                "risk_tolerance": tolerance,
                "horizon": horizon,
                "goal": data.goal,
                "monthly_amount": float(amount)
            }
            result["broker_analysis"] = analyze_portfolio(data.demat_holdings, onboarding_context)
            
            # Save imported portfolio
            await db_service.save_imported_portfolio(
                user_id=current_user.id,
                broker="broker",
                holdings=data.demat_holdings,
                analysis=result["broker_analysis"]
            )
            
        logger.info(f"Generated new investor suggest payload in INR. Total: {amount}")
        return safe_json(result)
        
    except Exception as e:
        logger.error(f"Error generating new investor onboarding response: {e}")
        raise HTTPException(status_code=500, detail=f"Onboarding calculation failed: {str(e)}")


@router.post("/existing")
async def onboarding_existing_investor(data: ExistingInvestorOnboarding, current_user = Depends(get_current_user)):
    """
    Processes onboarding details for an existing investor, computes a dynamic health score, 
    identifies gaps, and recommends a specific action today.
    """
    try:
        # Dynamic Health Score Calculation
        score = 50  # base
        
        # 1. Experience Years bonus
        if data.experience_years == "1–3 years":
            score += 10
        elif data.experience_years == "3–7 years":
            score += 15
        elif data.experience_years == "7+ years":
            score += 20
            
        # 2. Diversification (asset_types count)
        num_assets = len(data.asset_types)
        if 2 <= num_assets <= 4:
            score += 15
        elif num_assets > 4:
            score += 10  # over-diversification penalties
        elif num_assets == 1:
            score += 5
            
        # 3. Monthly Contribution consistency
        if data.monthly_contribution == "Nothing right now":
            score -= 10
        elif data.monthly_contribution == "Under ₹5,000":
            score += 5
        elif data.monthly_contribution == "₹5,000–₹20,000":
            score += 10
        elif data.monthly_contribution == "₹20,000–₹50,000":
            score += 15
        elif data.monthly_contribution == "₹50,000+":
            score += 20
            
        # Pain point scaling
        if data.pain_point in ["Don't know if I'm on track", "Too much to track manually", "Don't understand what I own"]:
            score -= 5
            
        # Bounds check
        health_score = max(15, min(100, score))
        
        # Determine top gap based on pain point
        if data.pain_point == "Don't know if I'm on track":
            top_gap = "Missing goal-based target modeling. You're investing without knowing if your current rate matches your retirement or wealth milestones."
        elif data.pain_point == "Too much to track manually":
            top_gap = "Portfolio tracking silo. With multiple brokers/apps, you have high friction tracking aggregate asset weights and performance metrics."
        elif data.pain_point == "Don't understand what I own":
            top_gap = "High stock overlapping risk. You have mutual funds or holdings that contain similar underlying shares, creating concentrated risk."
        elif data.pain_point == "Worried about risk":
            top_gap = "Undocumented drawdown exposure. Your current assets haven't been stress-tested against market shocks or interest rate shifts."
        elif data.pain_point == "Not getting good returns":
            top_gap = "Benchmark lag. Your allocations may suffer from high expense ratios or outdated actively managed structures lagging Nifty index returns."
        elif data.pain_point == "No time to manage it":
            top_gap = "Rebalancing drift. Your holdings have naturally drifted from your target risk profile, adding unintended volatility risk."
        else:
            top_gap = "Multi-broker segregation prevents unified analytics on risk, fees, and correlation metrics."
            
        # Determine action today based on preference and pain point
        if data.import_preference == "Yes, import from my broker statement":
            one_action_today = "Consolidate instantly. Upload your CDSL/NSDL CAS statement to unlock unified tracking and run automated rebalancing checks."
        elif data.import_preference == "I'll enter it manually":
            one_action_today = "Input your active SIP allocations to generate a stress-test report and find overlaps."
        else:
            one_action_today = "Import a broker statement as a read-only trial to instantly benchmark your fee leakages and index returns."
            
        result = {
            "health_score": health_score,
            "top_gap": top_gap,
            "one_action_today": one_action_today
        }
        
        # 4. Build and save custom strategy/portfolio inside the DB for the existing user
        try:
            portfolio_name = f"Rautrex Unified Strategy ({data.goal_type if 'yes' in data.goal_type.lower() else 'Wealth Builder'})"
            description_text = f"Personalised footprint strategy with health score {health_score}. Gaps: {top_gap}"
            
            # Standardize monthly contribution
            contrib = 0.0
            if "5,000–20,000" in data.monthly_contribution:
                contrib = 12500.0
            elif "20,000–50,000" in data.monthly_contribution:
                contrib = 35000.0
            elif "50,000+" in data.monthly_contribution:
                contrib = 50000.0
            elif "under" in data.monthly_contribution.lower():
                contrib = 2500.0
                
            await db_service.create_portfolio(
                user_id=current_user.id,
                name=portfolio_name,
                strategy="Unified",
                cash_balance=contrib,
                description=description_text
            )
            logger.info(f"Successfully saved customized existing footprint strategy portfolio in DB for user {current_user.id}")
        except Exception as db_err:
            logger.error(f"Failed to save customized existing footprint strategy portfolio in DB: {db_err}")
            
        # 5. Check if demat holdings are provided for analysis
        if data.demat_holdings:
            onboarding_context = {
                "investor_type": "existing",
                "risk_tolerance": "growth" if "not getting good returns" in str(data.pain_point).lower() or "growth" in str(data.goal_type).lower() else "balanced",
                "horizon": "3-7 years",
                "goal": data.goal_type,
                "monthly_amount": contrib
            }
            result["broker_analysis"] = analyze_portfolio(data.demat_holdings, onboarding_context)
            
            # Save imported portfolio
            await db_service.save_imported_portfolio(
                user_id=current_user.id,
                broker="broker",
                holdings=data.demat_holdings,
                analysis=result["broker_analysis"]
            )
            
        logger.info(f"Generated existing investor health report. Score: {health_score}")
        return safe_json(result)
        
    except Exception as e:
        logger.error(f"Error generating existing investor onboarding response: {e}")
        raise HTTPException(status_code=500, detail=f"Onboarding analytics failed: {str(e)}")


@router.post("/sync-demat")
async def onboarding_sync_demat(data: DematSyncRequest, current_user = Depends(get_current_user)):
    """
    Simulates securely syncing credentials and fetching holdings and available cash balance from user demat accounts.
    """
    try:
        broker_lower = data.broker.lower()
        
        # Build beautiful, premium mock data based on the selected broker to feel extremely real!
        if "zerodha" in broker_lower:
            cash_balance = 18400.0
            simulated_xirr = 16.4
            simulated_sip = 15000.0
            holdings = [
                # Stocks (8)
                { "ticker": "TCS.NS", "name": "Tata Consultancy Services Ltd", "asset_type": "equity", "sector": "Technology", "market_cap_type": "large", "shares": 15, "avg_cost": 3200.0, "current_price": 3450.0, "total_invested": 48000.0, "current_value": 51750.0, "pnl": 3750.0, "pnl_pct": 7.81, "expense_ratio": 0.0, "category": "" },
                { "ticker": "RELIANCE.NS", "name": "Reliance Industries Ltd", "asset_type": "equity", "sector": "Energy/Conglomerate", "market_cap_type": "large", "shares": 25, "avg_cost": 2100.0, "current_price": 2400.0, "total_invested": 52500.0, "current_value": 60000.0, "pnl": 7500.0, "pnl_pct": 14.28, "expense_ratio": 0.0, "category": "" },
                { "ticker": "HDFCBANK.NS", "name": "HDFC Bank Ltd", "asset_type": "equity", "sector": "Banking/Financial Services", "market_cap_type": "large", "shares": 35, "avg_cost": 1500.0, "current_price": 1650.0, "total_invested": 52500.0, "current_value": 57750.0, "pnl": 5250.0, "pnl_pct": 10.0, "expense_ratio": 0.0, "category": "" },
                { "ticker": "INFY.NS", "name": "Infosys Ltd", "asset_type": "equity", "sector": "Technology", "market_cap_type": "large", "shares": 30, "avg_cost": 1400.0, "current_price": 1520.0, "total_invested": 42000.0, "current_value": 45600.0, "pnl": 3600.0, "pnl_pct": 8.57, "expense_ratio": 0.0, "category": "" },
                { "ticker": "ICICIBANK.NS", "name": "ICICI Bank Ltd", "asset_type": "equity", "sector": "Banking/Financial Services", "market_cap_type": "large", "shares": 40, "avg_cost": 850.0, "current_price": 930.0, "total_invested": 34000.0, "current_value": 37200.0, "pnl": 3200.0, "pnl_pct": 9.41, "expense_ratio": 0.0, "category": "" },
                { "ticker": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "asset_type": "equity", "sector": "Automotive", "market_cap_type": "large", "shares": 60, "avg_cost": 550.0, "current_price": 615.0, "total_invested": 33000.0, "current_value": 36900.0, "pnl": 3900.0, "pnl_pct": 11.81, "expense_ratio": 0.0, "category": "" },
                { "ticker": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "asset_type": "equity", "sector": "Telecom", "market_cap_type": "large", "shares": 40, "avg_cost": 780.0, "current_price": 850.0, "total_invested": 31200.0, "current_value": 34000.0, "pnl": 2800.0, "pnl_pct": 8.97, "expense_ratio": 0.0, "category": "" },
                { "ticker": "LTIM.NS", "name": "LTIMindtree Ltd", "asset_type": "equity", "sector": "Technology", "market_cap_type": "large", "shares": 8, "avg_cost": 4800.0, "current_price": 5100.0, "total_invested": 38400.0, "current_value": 40800.0, "pnl": 2400.0, "pnl_pct": 6.25, "expense_ratio": 0.0, "category": "" },
                # Mutual Funds (4)
                { "ticker": "MIRAE_LARGECAP", "name": "Mirae Asset Large Cap Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 500.0, "avg_cost": 75.0, "current_price": 85.0, "total_invested": 37500.0, "current_value": 42500.0, "pnl": 5000.0, "pnl_pct": 13.33, "expense_ratio": 1.1, "category": "equity" },
                { "ticker": "AXIS_SMALLCAP", "name": "Axis Small Cap Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "small", "shares": 464.0, "avg_cost": 50.0, "current_price": 58.0, "total_invested": 23200.0, "current_value": 26912.0, "pnl": 3712.0, "pnl_pct": 16.0, "expense_ratio": 1.4, "category": "equity" },
                { "ticker": "SBI_BLUECHIP", "name": "SBI Blue Chip Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 300.0, "avg_cost": 60.0, "current_price": 68.0, "total_invested": 18000.0, "current_value": 20400.0, "pnl": 2400.0, "pnl_pct": 13.33, "expense_ratio": 1.2, "category": "equity" },
                { "ticker": "PP_FLEXICAP", "name": "Parag Parikh Flexi Cap Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 200.0, "avg_cost": 45.0, "current_price": 54.0, "total_invested": 9000.0, "current_value": 10800.0, "pnl": 1800.0, "pnl_pct": 20.0, "expense_ratio": 0.9, "category": "equity" },
                # ETFs (2)
                { "ticker": "GOLDBEES.NS", "name": "Nippon India Gold BeES", "asset_type": "etf", "sector": "Commodity", "market_cap_type": "large", "shares": 250, "avg_cost": 45.0, "current_price": 50.0, "total_invested": 11250.0, "current_value": 12500.0, "pnl": 1250.0, "pnl_pct": 11.11, "expense_ratio": 0.5, "category": "commodity" },
                { "ticker": "NIFTYBEES.NS", "name": "Nifty 50 ETF", "asset_type": "etf", "sector": "Diversified", "market_cap_type": "large", "shares": 60, "avg_cost": 190.0, "current_price": 215.0, "total_invested": 11400.0, "current_value": 12900.0, "pnl": 1500.0, "pnl_pct": 13.15, "expense_ratio": 0.2, "category": "equity" }
            ]
        elif "groww" in broker_lower:
            cash_balance = 8200.0
            simulated_xirr = 14.8
            simulated_sip = 10000.0
            holdings = [
                # Stocks (5)
                { "ticker": "ITC.NS", "name": "ITC Ltd", "asset_type": "equity", "sector": "FMCG/Consumer Goods", "market_cap_type": "large", "shares": 65, "avg_cost": 380.0, "current_price": 410.0, "total_invested": 24700.0, "current_value": 26650.0, "pnl": 1950.0, "pnl_pct": 7.89, "expense_ratio": 0.0, "category": "" },
                { "ticker": "ICICIBANK.NS", "name": "ICICI Bank Ltd", "asset_type": "equity", "sector": "Banking/Financial Services", "market_cap_type": "large", "shares": 35, "avg_cost": 850.0, "current_price": 930.0, "total_invested": 29750.0, "current_value": 32550.0, "pnl": 2800.0, "pnl_pct": 9.41, "expense_ratio": 0.0, "category": "" },
                { "ticker": "TATAMOTORS.NS", "name": "Tata Motors Ltd", "asset_type": "equity", "sector": "Automotive", "market_cap_type": "large", "shares": 45, "avg_cost": 550.0, "current_price": 615.0, "total_invested": 24750.0, "current_value": 27675.0, "pnl": 2925.0, "pnl_pct": 11.81, "expense_ratio": 0.0, "category": "" },
                { "ticker": "SBIN.NS", "name": "State Bank of India", "asset_type": "equity", "sector": "Banking/Financial Services", "market_cap_type": "large", "shares": 50, "avg_cost": 520.0, "current_price": 580.0, "total_invested": 26000.0, "current_value": 29000.0, "pnl": 3000.0, "pnl_pct": 11.53, "expense_ratio": 0.0, "category": "" },
                { "ticker": "WIPRO.NS", "name": "Wipro Ltd", "asset_type": "equity", "sector": "Technology", "market_cap_type": "large", "shares": 70, "avg_cost": 380.0, "current_price": 405.0, "total_invested": 26600.0, "current_value": 28350.0, "pnl": 1750.0, "pnl_pct": 6.57, "expense_ratio": 0.0, "category": "" },
                # Mutual Funds (5)
                { "ticker": "HDFC_FLEXICAP", "name": "HDFC Flexi Cap Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 300.0, "avg_cost": 75.0, "current_price": 86.0, "total_invested": 22500.0, "current_value": 25800.0, "pnl": 3300.0, "pnl_pct": 14.67, "expense_ratio": 1.05, "category": "equity" },
                { "ticker": "KOTAK_EMERGING", "name": "Kotak Emerging Equity Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "mid", "shares": 400.0, "avg_cost": 55.0, "current_price": 64.0, "total_invested": 22000.0, "current_value": 25600.0, "pnl": 3600.0, "pnl_pct": 16.36, "expense_ratio": 1.25, "category": "equity" },
                { "ticker": "AXIS_ELSS", "name": "Axis ELSS Tax Saver Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 250.0, "avg_cost": 65.0, "current_price": 72.0, "total_invested": 16250.0, "current_value": 18000.0, "pnl": 1750.0, "pnl_pct": 10.77, "expense_ratio": 1.15, "category": "equity" },
                { "ticker": "ICICI_BALANCED", "name": "ICICI Prudential Balanced Advantage Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 800.0, "avg_cost": 25.0, "current_price": 28.5, "total_invested": 20000.0, "current_value": 22800.0, "pnl": 2800.0, "pnl_pct": 14.0, "expense_ratio": 0.95, "category": "hybrid" },
                { "ticker": "SBI_MAGNUMGILT", "name": "SBI Magnum Gilt Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 600.0, "avg_cost": 40.0, "current_price": 43.5, "total_invested": 24000.0, "current_value": 26100.0, "pnl": 2100.0, "pnl_pct": 8.75, "expense_ratio": 0.88, "category": "debt" },
                # ETFs (1)
                { "ticker": "SBIGETFs", "name": "SBI Gold ETF", "asset_type": "etf", "sector": "Commodity", "market_cap_type": "large", "shares": 100, "avg_cost": 46.0, "current_price": 51.5, "total_invested": 4600.0, "current_value": 5150.0, "pnl": 550.0, "pnl_pct": 11.96, "expense_ratio": 0.55, "category": "commodity" }
            ]
        else: # upstox
            cash_balance = 12400.0
            simulated_xirr = 12.6
            simulated_sip = 8000.0
            holdings = [
                # Stocks (4)
                { "ticker": "SBIN.NS", "name": "State Bank of India", "asset_type": "equity", "sector": "Banking/Financial Services", "market_cap_type": "large", "shares": 40, "avg_cost": 520.0, "current_price": 580.0, "total_invested": 20800.0, "current_value": 23200.0, "pnl": 2400.0, "pnl_pct": 11.54, "expense_ratio": 0.0, "category": "" },
                { "ticker": "BHARTIARTL.NS", "name": "Bharti Airtel Ltd", "asset_type": "equity", "sector": "Telecom", "market_cap_type": "large", "shares": 25, "avg_cost": 780.0, "current_price": 850.0, "total_invested": 19500.0, "current_value": 21250.0, "pnl": 1750.0, "pnl_pct": 8.97, "expense_ratio": 0.0, "category": "" },
                { "ticker": "LTIM.NS", "name": "LTIMindtree Ltd", "asset_type": "equity", "sector": "Technology", "market_cap_type": "large", "shares": 5, "avg_cost": 4800.0, "current_price": 5100.0, "total_invested": 24000.0, "current_value": 25500.0, "pnl": 1500.0, "pnl_pct": 6.25, "expense_ratio": 0.0, "category": "" },
                { "ticker": "WIPRO.NS", "name": "Wipro Ltd", "asset_type": "equity", "sector": "Technology", "market_cap_type": "large", "shares": 60, "avg_cost": 380.0, "current_price": 405.0, "total_invested": 22800.0, "current_value": 24300.0, "pnl": 1500.0, "pnl_pct": 6.58, "expense_ratio": 0.0, "category": "" },
                # Mutual Funds (4)
                { "ticker": "UTI_NIFTY50", "name": "UTI Nifty 50 Index Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 250.0, "avg_cost": 100.0, "current_price": 112.5, "total_invested": 25000.0, "current_value": 28125.0, "pnl": 3125.0, "pnl_pct": 12.5, "expense_ratio": 0.2, "category": "equity" },
                { "ticker": "HDFC_BALANCED", "name": "HDFC Balanced Advantage Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 500.0, "avg_cost": 38.0, "current_price": 42.5, "total_invested": 19000.0, "current_value": 21250.0, "pnl": 2250.0, "pnl_pct": 11.84, "expense_ratio": 0.95, "category": "hybrid" },
                { "ticker": "NIPPON_LIQUID", "name": "Nippon India Liquid Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 10.0, "avg_cost": 2800.0, "current_price": 2980.0, "total_invested": 28000.0, "current_value": 29800.0, "pnl": 1800.0, "pnl_pct": 6.43, "expense_ratio": 0.25, "category": "debt" },
                { "ticker": "ABSL_CORPBOND", "name": "Aditya Birla Sun Life Corporate Bond Fund", "asset_type": "mutual_fund", "sector": "Diversified Mutual Fund", "market_cap_type": "large", "shares": 500.0, "avg_cost": 40.0, "current_price": 43.2, "total_invested": 20000.0, "current_value": 21600.0, "pnl": 1600.0, "pnl_pct": 8.0, "expense_ratio": 0.55, "category": "debt" },
                # ETFs (2)
                { "ticker": "GOLDBEES.NS", "name": "Nippon India Gold BeES", "asset_type": "etf", "sector": "Commodity", "market_cap_type": "large", "shares": 200, "avg_cost": 45.0, "current_price": 50.0, "total_invested": 9000.0, "current_value": 10000.0, "pnl": 1000.0, "pnl_pct": 11.11, "expense_ratio": 0.5, "category": "commodity" },
                { "ticker": "CPSEETF.NS", "name": "CPSE ETF", "asset_type": "etf", "sector": "Energy/Conglomerate", "market_cap_type": "large", "shares": 100, "avg_cost": 75.0, "current_price": 84.0, "total_invested": 7500.0, "current_value": 8400.0, "pnl": 900.0, "pnl_pct": 12.0, "expense_ratio": 0.05, "category": "equity" }
            ]

        # Standard Aggregation calculations
        total_invested = sum(h["total_invested"] for h in holdings)
        current_value = sum(h["current_value"] for h in holdings)
        overall_pnl = current_value - total_invested
        overall_pnl_pct = (overall_pnl / total_invested * 100.0) if total_invested > 0 else 0.0

        # Calculate Asset breakdown percentages
        equity_count = sum(1 for h in holdings if h["asset_type"] == "equity")
        equity_val = sum(h["current_value"] for h in holdings if h["asset_type"] == "equity")
        
        mf_count = sum(1 for h in holdings if h["asset_type"] == "mutual_fund")
        mf_val = sum(h["current_value"] for h in holdings if h["asset_type"] == "mutual_fund")
        
        etf_count = sum(1 for h in holdings if h["asset_type"] == "etf")
        etf_val = sum(h["current_value"] for h in holdings if h["asset_type"] == "etf")

        result = {
            "status": "success",
            "broker": data.broker,
            "holdings_count": len(holdings),
            "holdings": holdings,
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "overall_pnl": round(overall_pnl, 2),
            "overall_pnl_pct": round(overall_pnl_pct, 2),
            "cash_balance": cash_balance,
            "xirr": simulated_xirr,
            "active_sips": mf_count,
            "monthly_sip_amount": simulated_sip,
            "asset_type_breakdown": {
                "equity": {
                    "count": equity_count,
                    "value": round(equity_val, 2),
                    "pct": round(equity_val / current_value * 100.0, 2) if current_value > 0 else 0
                },
                "mutual_fund": {
                    "count": mf_count,
                    "value": round(mf_val, 2),
                    "pct": round(mf_val / current_value * 100.0, 2) if current_value > 0 else 0
                },
                "etf": {
                    "count": etf_count,
                    "value": round(etf_val, 2),
                    "pct": round(etf_val / current_value * 100.0, 2) if current_value > 0 else 0
                }
            }
        }
        
        # Save imported portfolio immediately into DB to ensure dashboard is ready
        analysis = analyze_portfolio(holdings, None)
        await db_service.save_imported_portfolio(
            user_id=current_user.id,
            broker=broker_lower,
            holdings=holdings,
            analysis=analysis
        )
        
        logger.info(f"User {current_user.id} successfully linked {data.broker} demat. Fetched total: INR {current_value}")
        return safe_json(result)
        
    except Exception as e:
        logger.error(f"Error syncing demat for user: {e}")
        raise HTTPException(status_code=500, detail=f"Demat connection failed: {str(e)}")


@router.post("/analyze-portfolio")
async def onboarding_analyze_portfolio(req: AnalyzePortfolioRequest, current_user = Depends(get_current_user)):
    """
    Analyzes imported broker portfolio data and returns detailed metrics, diversification scores, and personalized recommendations.
    """
    try:
        analysis = analyze_portfolio(req.holdings, req.onboarding_data)
        
        # Save to DB so it persists for the dashboard!
        broker_name = "Broker"
        if req.holdings:
            # Try to guess broker or default to "Broker"
            first_holding = req.holdings[0]
            first_ticker = str(first_holding.get("ticker") or "")
            if "TCS.NS" in first_ticker:
                broker_name = "zerodha"
            elif "ITC.NS" in first_ticker:
                broker_name = "groww"
            else:
                broker_name = "upstox"
                
        await db_service.save_imported_portfolio(
            user_id=current_user.id,
            broker=broker_name.lower(),
            holdings=req.holdings,
            analysis=analysis
        )
        
        return safe_json(analysis)
    except Exception as e:
        logger.error(f"Error in analyze-portfolio endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Portfolio analysis failed: {str(e)}")

@router.get("/imported-portfolio")
async def onboarding_get_imported_portfolio(current_user = Depends(get_current_user)):
    """
    Retrieves the user's previously imported broker portfolio and analysis.
    """
    try:
        portfolio = await db_service.get_imported_portfolio(current_user.id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="No imported portfolio found. Please sync your broker first.")
        return safe_json(portfolio)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving imported portfolio: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve imported portfolio: {str(e)}")

# --- PRODUCTION BR0KER MULTI-PATHWAY INTEGRATIONS ---

@router.get("/upstox-login")
async def upstox_login(current_user = Depends(get_current_user)):
    """
    Step 1 of Upstox OAuth: Redirects the user to Upstox's authorization server.
    """
    import urllib.parse
    client_id = os.getenv("UPSTOX_CLIENT_ID")
    redirect_uri = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/api/v1/onboarding/upstox-callback")
    
    if not client_id:
        raise HTTPException(status_code=500, detail="Upstox client ID not configured on server.")
        
    encoded_redirect = urllib.parse.quote(redirect_uri)
    auth_url = f"https://api.upstox.com/v2/oauth/authorize?client_id={client_id}&redirect_uri={encoded_redirect}&response_type=code"
    return {"auth_url": auth_url}

@router.get("/upstox-callback")
async def upstox_callback(code: str, current_user = Depends(get_current_user)):
    """
    Step 2 of Upstox OAuth: Exchange authorization code for access and refresh tokens.
    Then fetch initial holdings and run portfolio analysis.
    """
    try:
        from supabase_client import supabase
        import requests
        
        client_id = os.getenv("UPSTOX_CLIENT_ID")
        client_secret = os.getenv("UPSTOX_CLIENT_SECRET")
        redirect_uri = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/api/v1/onboarding/upstox-callback")
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Upstox credentials not configured on server.")
            
        token_url = "https://api.upstox.com/v2/oauth/token"
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        res = requests.post(token_url, data=payload, headers=headers, timeout=10)
        if res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Failed to exchange Upstox token: {res.text}")
            
        token_data = res.json()
        token_data["broker"] = "upstox"
        
        # Save tokens in profiles table under broker_oauth column
        supabase.table("profiles").update({"broker_oauth": token_data}).eq("id", current_user.id).execute()
        
        # Immediately fetch active holdings to populate the dashboard!
        access_token = token_data.get("access_token")
        holdings_url = "https://api.upstox.com/v2/portfolio/long-term-holdings"
        holdings_res = requests.get(holdings_url, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        
        holdings = []
        if holdings_res.status_code == 200:
            upstox_holdings = holdings_res.json().get("data") or []
            for h in upstox_holdings:
                ticker = f"{h.get('tradingsymbol')}.NS"
                shares = float(h.get("quantity") or 0.0)
                avg_cost = float(h.get("average_price") or 0.0)
                current_price = float(h.get("last_price") or avg_cost)
                
                holdings.append({
                    "ticker": ticker,
                    "name": h.get("company_name") or ticker,
                    "asset_type": "equity",
                    "sector": "Banking/Financial Services" if "BANK" in ticker else "Technology" if "TCS" in ticker or "INFY" in ticker else "Energy/Conglomerate",
                    "market_cap_type": "large",
                    "shares": shares,
                    "avg_cost": avg_cost,
                    "current_price": current_price,
                    "total_invested": shares * avg_cost,
                    "current_value": shares * current_price,
                    "pnl": shares * (current_price - avg_cost),
                    "pnl_pct": ((current_price - avg_cost) / avg_cost * 100.0) if avg_cost > 0 else 0.0,
                    "expense_ratio": 0.0,
                    "category": ""
                })
                
        # Analyze and save
        analysis = analyze_portfolio(holdings, None)
        await db_service.save_imported_portfolio(current_user.id, "upstox", holdings, analysis)
        
        return {
            "status": "success",
            "broker": "upstox",
            "holdings_count": len(holdings),
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Error in Upstox OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/email-webhook")
async def email_inbound_webhook(req_raw: Request = None):
    """
    Pathway 1: Mailgun/SendGrid Inbound Email Webhook.
    Receives email text forwarded by users, parses CDSL debit/credit alerts,
    and updates their holdings in real-time.
    """
    try:
        from fastapi import Request
        from supabase_client import supabase
        import re
        
        if req_raw is None:
            return {"status": "skipped", "reason": "No request data supplied."}
            
        # Parse transactional webhook payload
        form_data = await req_raw.form()
        recipient = str(form_data.get("recipient", ""))
        subject = str(form_data.get("subject", ""))
        body_text = str(form_data.get("body-plain", "")) or str(form_data.get("stripped-text", ""))
        
        # 1. Match recipient email to user alias (e.g. sync-john123@updates.rautrex.com)
        match = re.search(r'sync-([a-zA-Z0-9\-]+)@', recipient)
        if not match:
            return {"status": "skipped", "reason": "Recipient does not match expected sync alias format."}
            
        sync_alias = match.group(0)
        
        # Find user profile associated with this alias
        res = supabase.table("profiles").select("id").eq("email_sync_alias", sync_alias).execute()
        if not res.data:
            return {"status": "skipped", "reason": "No user registered with this email sync alias."}
            
        user_id = res.data[0]["id"]
        
        # 2. Parse CDSL Debit alert
        if "debit" in subject.lower() or "debit" in body_text.lower():
            isin_match = re.search(r'INE[A-Z0-9]{9}', body_text)
            qty_match = re.search(r'debit(?:ed)?\s+(\d+)\s+shares', body_text, re.IGNORECASE)
            
            if isin_match and qty_match:
                isin = isin_match.group(0)
                qty = int(qty_match.group(1))
                
                # Fetch existing imported portfolio
                pref_portfolio = await db_service.get_imported_portfolio(user_id)
                if pref_portfolio and "holdings" in pref_portfolio:
                    holdings = pref_portfolio["holdings"]
                    updated_holdings = []
                    
                    for h in holdings:
                        ticker = h.get("ticker", "")
                        # Simple match logic
                        if "TCS" in ticker and isin == "INE467B01029" or isin in str(h.get("name", "")):
                            shares = float(h.get("shares") or 0.0) - qty
                            if shares > 0:
                                h["shares"] = shares
                                h["total_invested"] = shares * h["avg_cost"]
                                h["current_value"] = shares * h["current_price"]
                                h["pnl"] = h["current_value"] - h["total_invested"]
                                updated_holdings.append(h)
                        else:
                            updated_holdings.append(h)
                            
                    # Re-run analysis and save
                    analysis = analyze_portfolio(updated_holdings, None)
                    await db_service.save_imported_portfolio(user_id, pref_portfolio.get("broker", "broker"), updated_holdings, analysis)
                    logger.info(f"Successfully processed email debit webhook for user {user_id}: Sold {qty} shares of {isin}.")
                    return {"status": "processed", "debit_detected": True, "isin": isin, "qty": qty}
                    
        return {"status": "skipped", "reason": "No valid transaction pattern detected in email text."}
        
    except Exception as e:
        logger.error(f"Error in email-webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-cas")
async def upload_cas_statement(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    current_user = Depends(get_current_user)
):
    """
    Pathway 1 (Alternative / Statement Upload): Parses an uploaded CDSL/NSDL CAS PDF,
    extracts holdings, performs portfolio analysis, and stores the synchronized data.
    """
    try:
        from services.cas_parser import parse_cas_pdf
        
        logger.info(f"Receiving CAS statement upload from user {current_user.id}...")
        
        # Read uploaded file bytes in-memory
        file_bytes = await file.read()
        
        # Parse PDF using the new CAS parser
        holdings = parse_cas_pdf(file_bytes, password=password)
        
        if not holdings:
            raise HTTPException(
                status_code=400, 
                detail="No valid holdings could be parsed from this statement. Please check the PDF format or password."
            )
            
        # Run portfolio analysis
        analysis = analyze_portfolio(holdings, None)
        
        # Save to DB (profile preferences and portfolios table)
        await db_service.save_imported_portfolio(
            user_id=current_user.id,
            broker="cas_statement",
            holdings=holdings,
            analysis=analysis
        )
        
        logger.info(f"Successfully processed CAS upload for user {current_user.id}: Parsed {len(holdings)} holdings.")
        return safe_json({
            "status": "success",
            "broker": "cas_statement",
            "holdings_count": len(holdings),
            "holdings": holdings,
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"Error parsing uploaded CAS statement: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to parse CAS statement: {str(e)}. If the PDF is password-protected, make sure you supplied the correct password."
        )


