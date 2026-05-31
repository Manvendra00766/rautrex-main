from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
import enum

class SignalType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class NotificationType(enum.Enum):
    SIGNAL = "signal"
    PRICE_ALERT = "price_alert"
    PORTFOLIO = "portfolio"
    SYSTEM = "system"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True) # Supabase UUID
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    avatar_url = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    portfolios = relationship("UserPortfolio", back_populates="user", cascade="all, delete-orphan")
    watchlists = relationship("Watchlist", back_populates="user", cascade="all, delete-orphan")
    backtests = relationship("SavedBacktest", back_populates="user", cascade="all, delete-orphan")
    signals = relationship("SavedSignal", back_populates="user", cascade="all, delete-orphan")
    simulations = relationship("SavedSimulation", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    price_alerts = relationship("PriceAlert", back_populates="user", cascade="all, delete-orphan")

class UserPortfolio(Base):
    __tablename__ = "user_portfolios"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    description = Column(String)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="portfolios")
    positions = relationship("PortfolioPosition", back_populates="portfolio", cascade="all, delete-orphan")

class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("user_portfolios.id"))
    ticker = Column(String, nullable=False)
    exchange = Column(String)
    shares = Column(Float, nullable=False)
    avg_cost_price = Column(Float, nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(String)
    
    portfolio = relationship("UserPortfolio", back_populates="positions")

class Watchlist(Base):
    __tablename__ = "watchlists"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="watchlists")
    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")

class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"))
    ticker = Column(String, nullable=False)
    exchange = Column(String)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    alert_price = Column(Float, nullable=True)
    
    watchlist = relationship("Watchlist", back_populates="items")

class SavedBacktest(Base):
    __tablename__ = "saved_backtests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    ticker = Column(String)
    strategy = Column(String)
    params = Column(JSON)
    results = Column(JSON)
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="backtests")

class SavedSignal(Base):
    __tablename__ = "saved_signals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ticker = Column(String, nullable=False)
    signal = Column(String) # BUY, SELL, HOLD
    confidence = Column(Float)
    breakdown = Column(JSON)
    was_correct = Column(Boolean, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="signals")

class SavedSimulation(Base):
    __tablename__ = "saved_simulations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    params = Column(JSON)
    summary_results = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="simulations")

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String) # signal, price_alert, portfolio, system
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    metadata_json = Column(JSON) # named metadata_json to avoid conflict with metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="notifications")

class PriceAlert(Base):
    __tablename__ = "price_alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ticker = Column(String, nullable=False)
    condition = Column(String) # above, below
    target_price = Column(Float, nullable=False)
    is_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    triggered_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="price_alerts")

class CompanyTickerMapping(Base):
    __tablename__ = "company_ticker_mappings"
    user_query = Column(String, primary_key=True, index=True) # Cleaned user query (lowercase, trimmed)
    resolved_ticker = Column(String, nullable=False, index=True) # Standard resolved ticker (e.g. AAPL)
    confidence_score = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PortfolioMetricsCache(Base):
    __tablename__ = "portfolio_metrics_cache"
    portfolio_id = Column(String, primary_key=True, index=True) # Linked to portfolio UUID or ID string
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    value_at_risk = Column(Float, default=0.0)
    beta = Column(Float, default=1.0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Instrument(Base):
    __tablename__ = "instruments"
    
    symbol = Column(String, primary_key=True, index=True) # e.g. AAPL, RELIANCE.NS
    name = Column(String, nullable=False)
    exchange = Column(String)
    currency = Column(String, default="USD")
    sector = Column(String)
    asset_type = Column(String, default="equity") # equity, commodity, crypto
    is_tracked = Column(Boolean, default=True) # If True, daily cron will sync this asset
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
