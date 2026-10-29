-- À exécuter dans l'éditeur SQL de Supabase
create table if not exists candidatures (
  id bigint generated always as identity primary key,
  created_at timestamptz default now(),
  source text default 'manuel',          -- manuel | email
  raw_text text not null,
  titre text, entreprise text, localisation text, contrat text,
  offre jsonb,                            -- offre structurée (EF03)
  matching jsonb,                         -- score, forces, écarts, suggestions CV (EF04-06)
  lettre text,                            -- EF07
  entretien jsonb,                        -- EF08
  statut text default 'À postuler',       -- EF09
  date_postule date,
  derniere_relance date,
  notes text default ''                   -- EF12
);

-- ===== RAG : Supabase Vector (pgvector) =====
create extension if not exists vector;

create table if not exists cv_chunks (
  id bigint generated always as identity primary key,
  cv_name text not null,
  content text not null,
  embedding vector(384)          -- paraphrase-multilingual-MiniLM-L12-v2 (FR/EN)
);
create index if not exists cv_chunks_emb_idx on cv_chunks using hnsw (embedding vector_cosine_ops);

create or replace function match_cv_chunks(query_embedding vector(384), p_cv_name text, match_count int default 5)
returns table (content text, similarity float)
language sql stable as $$
  select content, 1 - (embedding <=> query_embedding) as similarity
  from cv_chunks where cv_name = p_cv_name
  order by embedding <=> query_embedding limit match_count;
$$;

-- RGPD : RLS activée. L'app utilise la clé service_role côté serveur uniquement.
alter table cv_chunks enable row level security;
alter table candidatures enable row level security;
