import datetime
from zoneinfo import ZoneInfo
from typing import Tuple, Dict, Any, Optional
from core.logger import logger
from infrastructure.time_sync import offset_calibrated_now

class MarketCalendarService:
    """
    MarketCalendarService handles operational trading calendars for US and Indian stock markets.
    It verifies trading hours, weekends, and holiday schedules using calibrated atomic time to
    prevent sending orders or API requests when markets are closed.
    """
    def __init__(self):
        self.us_tz = ZoneInfo("America/New_York")
        self.in_tz = ZoneInfo("Asia/Kolkata")
        
        # Hardcoded fixed holidays for US and India (YYYY-MM-DD format)
        # Extending to cover 2026 and 2027 for bulletproof production performance
        self.us_holidays = {
            # 2026 US
            "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
            "2026-06-19", "2026-07-04", "2026-09-07", "2026-11-26", "2026-12-25",
            # 2027 US
            "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
            "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
        }
        
        self.in_holidays = {
            # 2026 India
            "2026-01-26", "2026-03-06", "2026-03-24", "2026-04-02", "2026-04-14",
            "2026-05-01", "2026-08-15", "2026-10-02", "2026-10-22", "2026-11-12",
            "2026-12-25",
            # 2027 India
            "2027-01-26", "2027-03-12", "2027-03-22", "2027-04-09", "2027-04-14",
            "2027-05-01", "2027-08-15", "2027-10-02", "2027-10-11", "2027-11-01",
            "2027-12-25",
        }

    def _get_market_tz_and_hours(self, symbol: str) -> Tuple[ZoneInfo, datetime.time, datetime.time, str]:
        """Resolves market timezone and standard trading hours for a given symbol."""
        symbol_upper = symbol.strip().upper()
        # Indian equities check
        if symbol_upper.endswith(".NS") or symbol_upper.endswith(".BO") or "GS" in symbol_upper or "GB" in symbol_upper:
            # Indian markets trade 9:15 AM - 3:30 PM IST
            return self.in_tz, datetime.time(9, 15), datetime.time(15, 30), "IN"
        
        # Default US equities (9:30 AM - 4:00 PM EST)
        return self.us_tz, datetime.time(9, 30), datetime.time(16, 0), "US"

    def is_market_open(self, symbol: str, dt: Optional[datetime.datetime] = None) -> bool:
        """
        Checks if the market for the given symbol is currently open.
        dt: Optional datetime. If not provided, utilizes calibrated atomic now time.
        """
        if dt is None:
            # Use offset-calibrated epoch timestamp
            dt = datetime.datetime.fromtimestamp(offset_calibrated_now(), tz=datetime.timezone.utc)
            
        tz, open_time, close_time, region = self._get_market_tz_and_hours(symbol)
        
        # Convert check time to the market's timezone
        local_dt = dt.astimezone(tz)
        
        # Check weekends
        if local_dt.weekday() >= 5: # Saturday=5, Sunday=6
            return False
            
        # Check holidays
        date_str = local_dt.strftime("%Y-%m-%d")
        if region == "US" and date_str in self.us_holidays:
            return False
        if region == "IN" and date_str in self.in_holidays:
            return False
            
        # Check time within open/close range
        current_time = local_dt.time()
        return open_time <= current_time <= close_time

    def get_market_status(self, symbol: str) -> Dict[str, Any]:
        """Returns structured metadata about the market session status for a given ticker."""
        tz, open_time, close_time, region = self._get_market_tz_and_hours(symbol)
        now_dt = datetime.datetime.fromtimestamp(offset_calibrated_now(), tz=datetime.timezone.utc)
        local_now = now_dt.astimezone(tz)
        
        is_open = self.is_market_open(symbol, now_dt)
        
        return {
            "region": region,
            "timezone": str(tz),
            "is_open": is_open,
            "local_time": local_now.isoformat(),
            "market_hours": f"{open_time.strftime('%H:%M')} - {close_time.strftime('%H:%M')}",
            "weekend": local_now.weekday() >= 5,
            "holiday": (local_now.strftime("%Y-%m-%d") in self.us_holidays) if region == "US" else (local_now.strftime("%Y-%m-%d") in self.in_holidays)
        }

market_calendar = MarketCalendarService()
