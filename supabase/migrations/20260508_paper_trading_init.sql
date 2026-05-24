-- Paper Trading Tables
CREATE TABLE IF NOT EXISTS public.paper_accounts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    cash_balance float8 DEFAULT 1000000,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.paper_positions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker text NOT NULL,
    quantity int NOT NULL,
    avg_buy_price float8 NOT NULL,
    UNIQUE(user_id, ticker)
);

CREATE TABLE IF NOT EXISTS public.paper_orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker text NOT NULL,
    side text NOT NULL,
    quantity int NOT NULL,
    order_type text NOT NULL,
    limit_price float8,
    executed_price float8,
    status text NOT NULL,
    created_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.paper_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.paper_positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.paper_orders ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY paper_accounts_user_policy ON public.paper_accounts
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY paper_positions_user_policy ON public.paper_positions
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY paper_orders_user_policy ON public.paper_orders
    FOR ALL USING (auth.uid() = user_id);
