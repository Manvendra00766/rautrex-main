# Production Alignment Plan

This plan removes the localhost-versus-production gap by making production self-sufficient for portfolio truth, broker auth, and market data.

## Implemented First

- Imported portfolio ledgers now synthesize an opening cash baseline when no real deposit exists, preventing negative cash and distorted NAV.
- Synthetic position snapshots remain cash-neutral so imported holdings do not inflate NAV.
- Production now disables yfinance fallback by default. yfinance remains available in local/test environments, or only when `ALLOW_YFINANCE_FALLBACK=true` is explicitly set.

## Implementation Phases

1. Cash and NAV correctness
   - Keep imported broker portfolios from going negative when deposit rows are missing.
   - Store or derive an auditable opening balance for imported transaction ledgers.

2. Supabase as source of truth
   - Use Supabase for local and production portfolio state.
   - Stop relying on `rautrex.db` for any data production needs.
   - Keep dev/prod separated by project or schema, not by code path.

3. Production-safe market data
   - Upstox for Indian holdings and live Indian prices.
   - Alpaca/TwelveData for supported global quotes.
   - Cached values before provider fetches.
   - Synthetic data only for optimizer continuity, never as real portfolio truth.

4. Persistent historical price cache
   - Add a durable `price_history_cache` table in Supabase.
   - Read historical candles from cache first.
   - Fetch only missing ranges from providers.
   - Cache historical candles permanently because past closes are stable.

5. Upstox OAuth reconnect flow
   - Add a dashboard "Connect Upstox" action.
   - Redirect through the official Upstox OAuth URL.
   - Store token metadata in Supabase.
   - Show connected, expired, and fallback states in the UI.

6. Production health checks
   - Expose Supabase, Redis, Upstox token, TwelveData key, and latest price-sync status.
   - Surface degraded/fallback mode clearly in the dashboard.

## Manual Work Required

- In Hugging Face/Vercel environment settings, set:
  - `ENVIRONMENT=production`
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_JWT_SECRET`
  - `REDIS_URL`
  - `TWELVEDATA_API_KEY`
  - `ALPACA_API_KEY_ID` and `ALPACA_SECRET_KEY` if using Alpaca
  - `UPSTOX_CLIENT_ID`, `UPSTOX_CLIENT_SECRET`, and `UPSTOX_REDIRECT_URI`
- Do not set `ALLOW_YFINANCE_FALLBACK=true` in production unless you are deliberately testing a fallback.
- In the Upstox developer console, configure the exact production OAuth redirect URI.
- Apply all Supabase migrations to the production project before switching traffic.
- Seed or import current broker portfolio data into Supabase, not local SQLite.
