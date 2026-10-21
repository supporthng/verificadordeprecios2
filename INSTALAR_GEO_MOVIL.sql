-- Ejecutar una sola vez en Supabase > SQL Editor.
-- La tabla no se expone a anon/authenticated: acceso solo mediante service_role del servidor.
create table if not exists public.mobile_geo_settings (
  id integer primary key check (id = 1),
  enabled boolean not null default true,
  latitude double precision not null default 0 check (latitude between -90 and 90),
  longitude double precision not null default 0 check (longitude between -180 and 180),
  radius_m integer not null default 100 check (radius_m = 100)
);
alter table public.mobile_geo_settings enable row level security;
revoke all on public.mobile_geo_settings from anon, authenticated;
insert into public.mobile_geo_settings (id, enabled, latitude, longitude, radius_m)
values (1, true, 0, 0, 100)
on conflict (id) do nothing;
-- IMPORTANTE: 0,0 no es la ubicación del negocio. Configúrala desde Administración.
