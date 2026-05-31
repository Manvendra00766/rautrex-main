import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.logger import logger
from models.user_data import PortfolioPosition

class CorporateActionsService:
    def __init__(self):
        self.log_dir = r"D:\projects\rautrex-main\logs"
        self.log_file = os.path.join(self.log_dir, "corporate_actions.log")
        
        # Ensure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup specific file logger for splits audit trail
        self.audit_logger = logging.getLogger("CorporateActionsAudit")
        self.audit_logger.setLevel(logging.INFO)
        if not self.audit_logger.handlers:
            fh = logging.FileHandler(self.log_file)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.audit_logger.addHandler(fh)

    async def ingest_splits_and_dividends(self, db: AsyncSession):
        """
        Runs overnight at 4:00 AM. Detects active stock splits (e.g., AAPL 2-for-1 split)
        and adjusts holding shares and cost basis atomically to prevent portfolio NAV swings.
        """
        logger.info("[CorporateActions] Running overnight corporate actions scanner...")
        
        # Simulated Corporate Action feeds. In production, pull from Alpaca/Upstox API
        mock_events = [
            {"ticker": "AAPL", "event_type": "SPLIT", "ratio": 2.0, "effective_date": "2026-05-30"},
            {"ticker": "SUZLON.NS", "event_type": "SPLIT", "ratio": 5.0, "effective_date": "2026-05-30"}
        ]

        for event in mock_events:
            ticker = event["ticker"]
            ratio = event["ratio"]
            
            try:
                # Retrieve all active positions holding this ticker
                stmt = select(PortfolioPosition).where(PortfolioPosition.ticker == ticker)
                res = await db.execute(stmt)
                positions = res.scalars().all()
                
                if not positions:
                    continue
                
                logger.info(f"[CorporateActions] Processing {event['event_type']} for {ticker} (Ratio: {ratio}). Updating {len(positions)} holdings...")
                
                # Apply adjustments atomically
                updated_count = 0
                for pos in positions:
                    old_shares = pos.shares
                    old_cost = pos.avg_cost_price
                    
                    # Apply 2-for-1 split (shares double, price halves)
                    new_shares = old_shares * ratio
                    new_cost = old_cost / ratio
                    
                    pos.shares = new_shares
                    pos.avg_cost_price = new_cost
                    updated_count += 1
                    
                    # Audit log details
                    log_msg = (
                        f"SUCCESS - Position ID {pos.id} (Portfolio {pos.portfolio_id}) "
                        f"Adjusted: Ticker={ticker}, Shares: {old_shares} -> {new_shares}, "
                        f"Cost Basis: INR/USD {old_cost:.2f} -> {new_cost:.2f}"
                    )
                    self.audit_logger.info(log_msg)
                
                # Commit all updates inside one atomic database transaction block
                await db.commit()
                
                summary = f"SPLIT APPLIED: Ticker={ticker}, Ratio={ratio}. Updated {updated_count} positions successfully."
                self.audit_logger.info(summary)
                logger.info(f"[CorporateActions] {summary}")
                
            except Exception as e:
                logger.error(f"[CorporateActions] Failed applying split for {ticker}: {e}")
                await db.rollback()
                self.audit_logger.error(f"FAILURE - Split error for {ticker}: {e}")

corporate_actions_service = CorporateActionsService()
