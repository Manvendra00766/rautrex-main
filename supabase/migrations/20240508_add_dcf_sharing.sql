-- SQL migration for Public Sharing of DCF Valuations

-- Add is_public column to dcf_valuations
ALTER TABLE dcf_valuations 
ADD COLUMN is_public BOOLEAN DEFAULT FALSE;

-- Update RLS policies to allow public read access
CREATE POLICY "Public can view public valuations" 
ON dcf_valuations FOR SELECT 
USING (is_public = TRUE);

-- Update existing user policy to ensure they can still see their private ones
-- (The existing "Users can view their own DCF valuations" policy already handles this)
