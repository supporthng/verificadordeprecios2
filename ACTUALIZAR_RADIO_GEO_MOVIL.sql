-- Ejecutar UNA VEZ en Supabase > SQL Editor antes de usar el radio editable.
-- Quita la restricción anterior que obligaba a radius_m = 100.
ALTER TABLE public.mobile_geo_settings
  DROP CONSTRAINT IF EXISTS mobile_geo_settings_radius_m_check;
ALTER TABLE public.mobile_geo_settings
  ADD CONSTRAINT mobile_geo_settings_radius_m_check
  CHECK (radius_m BETWEEN 10 AND 10000);
