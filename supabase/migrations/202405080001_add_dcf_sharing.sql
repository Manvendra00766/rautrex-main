-- SQL migration for Public Sharing of DCF Valuations

-- Add is_public column to dcf_valuations
ALTER TABLE dcf_valuations
ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;

-- Update RLS policies to allow public read access
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'dcf_valuations'
          AND policyname = 'Public can view public valuations'
    ) THEN
        CREATE POLICY "Public can view public valuations"
        ON dcf_valuations FOR SELECT
        USING (is_public = TRUE);
    END IF;
END $$;

-- Update existing user policy to ensure they can still see their private ones
-- (The existing "Users can view their own DCF valuations" policy already handles this)
