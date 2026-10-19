-- Ejecutar una vez en Supabase SQL Editor. No altera tablas existentes.
CREATE TABLE IF NOT EXISTS public.external_catalog_jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 configuration_id uuid NOT NULL REFERENCES public.external_price_sources(id),
 page_number integer NOT NULL CHECK (page_number >= 1),
 page_size integer NOT NULL CHECK (page_size BETWEEN 1 AND 100),
 search_term text NOT NULL DEFAULT '',
 status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','done','error')),
 result jsonb, error_message text,
 created_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz NOT NULL DEFAULT (now() + interval '3 minutes')
);
CREATE INDEX IF NOT EXISTS external_catalog_jobs_pending_idx
 ON public.external_catalog_jobs (status, created_at);
ALTER TABLE public.external_catalog_jobs ENABLE ROW LEVEL SECURITY;
-- Sin políticas públicas: solo service_role del servidor.
