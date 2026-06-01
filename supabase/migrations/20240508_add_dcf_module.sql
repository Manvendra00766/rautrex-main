-- FILE 4: SQL migration for DCF Module

-- Create dcf_valuations table
CREATE TABLE IF NOT EXISTS dcf_valuations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    input_data JSONB NOT NULL,
    output_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE dcf_valuations ENABLE ROW LEVEL SECURITY;

-- Policies
-- 1. Users can insert their own DCF valuations
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'dcf_valuations'
          AND policyname = 'Users can insert their own DCF valuations'
    ) THEN
        CREATE POLICY "Users can insert their own DCF valuations"
        ON dcf_valuations FOR INSERT
        WITH CHECK (auth.uid() = user_id);
    END IF;
END $$;

-- 2. Users can view their own DCF valuations
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'dcf_valuations'
          AND policyname = 'Users can view their own DCF valuations'
    ) THEN
        CREATE POLICY "Users can view their own DCF valuations"
        ON dcf_valuations FOR SELECT
        USING (auth.uid() = user_id);
    END IF;
END $$;

-- 3. Users can delete their own DCF valuations
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'dcf_valuations'
          AND policyname = 'Users can delete their own DCF valuations'
    ) THEN
        CREATE POLICY "Users can delete their own DCF valuations"
        ON dcf_valuations FOR DELETE
        USING (auth.uid() = user_id);
    END IF;
END $$;

-- main.py Registration Lines (Summary of changes applied):
-- 1. Added dcf_router to imports from routers
-- 2. Added app.include_router(dcf_router.router, prefix="/api/v1/dcf", tags=["DCF Valuation"])
