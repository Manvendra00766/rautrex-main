-- Migration: Add margin_enabled to portfolios
ALTER TABLE public.portfolios 
ADD COLUMN IF NOT EXISTS margin_enabled BOOLEAN DEFAULT FALSE;
