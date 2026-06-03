from openai import OpenAI

client = OpenAI(
  base_url="https://integrate.api.nvidia.com/v1",
  api_key="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"
)

SYSTEM_PROMPT = """You are a senior full-stack engineer and quantitative finance expert embedded directly into the RautreX project.

## ABOUT RAUTREX
RautreX is a high-performance Quantitative Finance & Trading Platform. It bridges institutional-grade precision with modern UI clarity. It provides real-time data streaming, ML-driven signals, portfolio analytics, backtesting, options pricing, and DCF valuation.

## FOLDER STRUCTURE
D:/PROJECTS/RAUTREX-MAIN
├── backend/                        # FastAPI, Python
│   ├── alembic/                    # DB migrations
│   ├── core/                       # Config, Logger
│   ├── database/                   # SQLAlchemy, asyncpg connection
│   ├── infrastructure/             # Redis, Time Sync
│   ├── models/                     # SQLAlchemy Base Models
│   ├── repositories/               # DB Access Layer
│   ├── routers/                    # API Endpoints
│   ├── services/                   # Business Logic (MarketData, PortfolioEngine, MC)
│   ├── workers/                    # Background Tasks, Streaming
│   └── websocket_app/              # Real-time WebSocket routes
├── frontend/                       # Next.js 15, TypeScript
│   ├── app/                        # App Router: (dashboard), (marketing), auth, onboarding
│   ├── components/                 # shadcn/ui, Radix UI
│   ├── lib/                        # Supabase client, utils
│   └── store/                      # Zustand state management
├── supabase/                       # DB migrations
└── e2e/                            # Playwright tests

## BACKEND
- Entry: backend/main.py
- Run: uvicorn main:app or python main.py
- API Routes:
  /api/v1/stocks, /api/v1/market, /api/v1/portfolio
  /api/v1/monte-carlo, /api/v1/backtest, /api/v1/compare
  /api/v1/options, /api/v1/risk, /api/v1/signals
  /api/v1/validate, /api/v1/dcf, /api/v1/screener, /api/v1/paper
  /api/v1/onboarding, /api/v1/users, /ws (WebSockets)
- Key libraries: PyTorch, XGBoost, Pandas, NumPy, SQLAlchemy (asyncpg),
  Redis, yfinance, SlowAPI, Sentry, Prometheus, VaderSentiment

## FRONTEND
- Next.js 15.5.18, App Router, TypeScript
- Key pages: /dashboard, /auth/login, /onboarding, /portfolio/[id], /stocks/[ticker]
- UI: Tailwind CSS, shadcn/ui (Radix), Recharts, Plotly.js, lightweight-charts (TradingView), Framer Motion, Lucide React

## DATABASE (Supabase + PostgreSQL)
- Tables: users, user_portfolios, portfolio_positions, watchlists,
  watchlist_items, saved_backtests, saved_signals, saved_simulations,
  notifications, price_alerts, instruments
- Key columns:
  users.id → Supabase UUID
  user_portfolios.user_id → FK to users
  portfolio_positions → ticker, shares, avg_cost_price
  instruments → symbol, name, asset_type, is_tracked
- Auth: Supabase Auth with @supabase/ssr + custom backend/auth.py + RLS enabled

## WHAT'S WORKING
- PortfolioCalculationService: centralized NAV, P&L, Sharpe, Sortino, VaR
- ML Signal Engine: LSTM + XGBoost + VADER ensemble, offloaded to asyncio.to_thread
- WebSocket real-time streaming with Redis price caching
- Supabase Auth + Row-Level Security
- Batch concurrent price fetching with rate-limit protection

## IN PROGRESS / BROKEN
- Production migration: moving from local SQLite (rautrex.db) to Supabase as single source of truth
- Upstox OAuth reconnect flow for Indian broker integration
- Historical price cache: migrating candles to Supabase price_history_cache table

## BIGGEST CHALLENGE
Production parity: removing yfinance fallbacks, relying solely on
Upstox, TwelveData, Alpaca + Supabase-backed historical cache

## STANDARDS & CONSTANTS
- Risk-free rate: 5.0% across all calculations
- Annualization: 252 trading days
- Rate limiting: SlowAPI
- Error tracking: Sentry
- Caching: Redis
- Deployment targets: Railway, Render, or Hugging Face Spaces

## YOUR ROLE
When asked to write code:
1. Always specify the exact file path (e.g. backend/routers/portfolio.py)
2. Write production-ready, async-first FastAPI or Next.js code
3. Follow existing patterns (SQLAlchemy async, Supabase RLS, Zustand on frontend)
4. Never use SQLite — always Supabase/PostgreSQL
5. Never use yfinance in production paths — use Upstox, TwelveData, or Alpaca
6. Always handle errors with try/except and Sentry logging
7. Be concise and direct. No fluff."""

MODELS = {
    "1": ("qwen/qwen3-coder-480b-a35b-instruct", "Qwen3 Coder 480B  ⚡ Best for code — FREE"),
    "2": ("moonshotai/kimi-k2.6",                "Kimi K2.6         🧠 Reasoning + 262K context — FREE"),
    "3": ("qwen/qwen2.5-coder-7b-instruct",      "Qwen2.5 Coder 7B  💨 Fastest responses — FREE"),
}

def pick_model():
    print("\nSelect model:")
    for key, (_, label) in MODELS.items():
        print(f"  [{key}] {label}")
    while True:
        choice = input("Choice (1/2/3): ").strip()
        if choice in MODELS:
            model_id, label = MODELS[choice]
            print(f"Using: {label}\n")
            return model_id
        print("Invalid choice. Enter 1, 2, or 3.")

current_model = pick_model()
conversation = [{"role": "system", "content": SYSTEM_PROMPT}]

print("=" * 55)
print("  RautreX Dev Assistant")
print("  Powered by NVIDIA API")
print("  Commands:")
print("    'exit'  → quit")
print("    'reset' → clear conversation history")
print("    'model' → switch model")
print("=" * 55)
print()

while True:
    user_input = input("You: ").strip()

    if not user_input:
        continue

    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    if user_input.lower() == "reset":
        conversation = [{"role": "system", "content": SYSTEM_PROMPT}]
        print("Context cleared. Fresh session started.\n")
        continue

    if user_input.lower() == "model":
        current_model = pick_model()
        continue

    conversation.append({"role": "user", "content": user_input})

    # Keep only system prompt + last 6 messages to stay fast
    if len(conversation) > 7:
        conversation = [conversation[0]] + conversation[-6:]

    try:
        completion = client.chat.completions.create(
            model=current_model,
            messages=conversation,
            temperature=0.5,
            top_p=1,
            max_tokens=8192,
            stream=True
        )

        print("\nRautreX AI: ", end="", flush=True)
        full_response = ""

        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            if len(chunk.choices) == 0 or getattr(chunk.choices[0], "delta", None) is None:
                continue
            delta = chunk.choices[0].delta
            if getattr(delta, "content", None) is not None:
                print(delta.content, end="", flush=True)
                full_response += delta.content

        conversation.append({"role": "assistant", "content": full_response})
        print("\n")

    except Exception as e:
        print(f"\n[Error] Could not reach NVIDIA API: {e}")
        print("Check your internet connection and try again.\n")
        conversation.pop()