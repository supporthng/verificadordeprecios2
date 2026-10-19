-- Ejecutar una sola vez en Supabase > SQL Editor.
-- Solo el backend con SERVICE_ROLE_KEY podrá acceder a esta tabla.
create table if not exists public.verificador_usuarios (
    id uuid primary key default gen_random_uuid(),
    username text not null unique,
    password_hash text not null,
    role text not null default 'usuario' check (role in ('admin', 'usuario')),
    permissions text[] not null default '{}',
    active boolean not null default true,
    must_change_password boolean not null default true,
    created_at timestamptz not null default now()
);
alter table public.verificador_usuarios enable row level security;
revoke all on public.verificador_usuarios from anon, authenticated;
-- No crear políticas públicas. SERVICE_ROLE_KEY omite RLS.
