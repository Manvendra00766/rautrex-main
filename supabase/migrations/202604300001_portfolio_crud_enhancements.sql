-- Migration: Portfolio CRUD + Portfolio Positions Management
-- Update portfolios table
ALTER TABLE public.portfolios 
ADD COLUMN IF NOT EXISTS strategy TEXT,
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS cash_balance NUMERIC(20, 8) DEFAULT 0;

-- Enable RLS on portfolios
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;

-- Add RLS policies for portfolios
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'portfolios' AND policyname = 'portfolios_select_own'
    ) THEN
        CREATE POLICY portfolios_select_own ON public.portfolios
            FOR SELECT USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'portfolios' AND policyname = 'portfolios_insert_own'
    ) THEN
        CREATE POLICY portfolios_insert_own ON public.portfolios
            FOR INSERT WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'portfolios' AND policyname = 'portfolios_update_own'
    ) THEN
        CREATE POLICY portfolios_update_own ON public.portfolios
            FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'portfolios' AND policyname = 'portfolios_delete_own'
    ) THEN
        CREATE POLICY portfolios_delete_own ON public.portfolios
            FOR DELETE USING (auth.uid() = user_id);
    END IF;
END $$;

-- Create portfolio_positions table (Standardized name)
CREATE TABLE IF NOT EXISTS public.portfolio_positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES public.portfolios(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    shares NUMERIC(20, 8) NOT NULL DEFAULT 0,
    avg_cost_price NUMERIC(20, 8) NOT NULL DEFAULT 0,
    exchange TEXT DEFAULT 'NASDAQ',
    asset_type TEXT NOT NULL DEFAULT 'Stock',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    deleted_at TIMESTAMPTZ
);

-- Ensure transactions table matches expectations if not already handled
-- (The existing transactions table in institutional_portfolio_core is quite complete)
-- We'll just add an index for portfolio_positions
CREATE INDEX IF NOT EXISTS idx_portfolio_positions_portfolio_id ON public.portfolio_positions(portfolio_id);

-- Enable RLS on portfolio_positions
ALTER TABLE public.portfolio_positions ENABLE ROW LEVEL SECURITY;

-- Add RLS policies for portfolio_positions
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'portfolio_positions' AND policyname = 'portfolio_positions_select_own'
    ) THEN
        CREATE POLICY portfolio_positions_select_own ON public.portfolio_positions
            FOR SELECT USING (
                EXISTS (
                    SELECT 1 FROM public.portfolios 
                    WHERE id = portfolio_positions.portfolio_id AND user_id = auth.uid()
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'portfolio_positions' AND policyname = 'portfolio_positions_insert_own'
    ) THEN
        CREATE POLICY portfolio_positions_insert_own ON public.portfolio_positions
            FOR INSERT WITH CHECK (
                EXISTS (
                    SELECT 1 FROM public.portfolios 
                    WHERE id = portfolio_positions.portfolio_id AND user_id = auth.uid()
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'portfolio_positions' AND policyname = 'portfolio_positions_update_own'
    ) THEN
        CREATE POLICY portfolio_positions_update_own ON public.portfolio_positions
            FOR UPDATE USING (
                EXISTS (
                    SELECT 1 FROM public.portfolios 
                    WHERE id = portfolio_positions.portfolio_id AND user_id = auth.uid()
                )
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'portfolio_positions' AND policyname = 'portfolio_positions_delete_own'
    ) THEN
        CREATE POLICY portfolio_positions_delete_own ON public.portfolio_positions
            FOR DELETE USING (
                EXISTS (
                    SELECT 1 FROM public.portfolios 
                    WHERE id = portfolio_positions.portfolio_id AND user_id = auth.uid()
                )
            );
    END IF;
END $$;
