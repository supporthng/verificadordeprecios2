-- Ejecutar una sola vez en SQL Editor de Supabase.
create table if not exists public.cloud_price_sources (
 id integer primary key check (id=1),
 kind text not null check (kind in ('excel','sheets')),
 file_id text not null,
 sheet_name text not null default '',
 code_column text not null,
 description_column text not null,
 price_column text not null
);
-- La columna source_type puede tener un CHECK preexistente que solo admita local/external.
-- Amplíalo para admitir cloud (ajusta el nombre de la restricción si es diferente).
do $$
declare r record;
begin
 for r in select conname from pg_constraint
  where conrelid='public.price_source_settings'::regclass and contype='c'
    and pg_get_constraintdef(oid) ilike '%source_type%'
 loop
  execute format('alter table public.price_source_settings drop constraint %I',r.conname);
 end loop;
end $$;
alter table public.price_source_settings
 add constraint price_source_settings_source_type_check
 check (source_type in ('local','external','cloud'));
revoke all on public.cloud_price_sources from anon, authenticated;
