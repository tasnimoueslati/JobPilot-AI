# 🧭 JobPilot AI — Assistant de candidatures (MVP)

Flux : offre (email via n8n / copier-coller / PDF) → **Agent Offre** → **Agent Matching (RAG pgvector sur CV)** → **Lettre** + **Préparation entretien** → pipeline + rappels Telegram.

## Architecture
| Composant | Fichier |
|---|---|
| Agents + coordinateur LangGraph | `app/agents.py` |
| RAG (Supabase Vector + FastEmbed) | `app/rag.py`, `schema.sql` |
| Base Supabase | `app/db.py`, `schema.sql` |
| Notifications / relances | `app/notifier.py` |
| Interface | `streamlit_app.py` |

## Installation
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # clés : Groq (gratuit), Supabase, Telegram (@BotFather)
# Supabase : coller schema.sql dans le SQL Editor (active pgvector)
# Utiliser la clé service_role dans SUPABASE_KEY (serveur uniquement, jamais côté navigateur)
streamlit run streamlit_app.py
```

## n8n (ingestion email + rappels)
1. **Ingestion (EF01)** : `Gmail Trigger` (label « Offres ») → `Code` (nettoyer le HTML en texte) → `Supabase` *Insert* dans `candidatures` avec `source='email'` et `raw_text`.
   Dans l'app : onglet « Nouvelle offre » → « Analyser les offres en attente ».
2. **Rappels (EF10)** : `Schedule Trigger` (chaque matin) → `Execute Command` : `python -m app.notifier`.

## Démo
Charger un CV PDF → coller une offre → score + lettre + 8 questions → passer en « Postulé » → `python -m app.notifier` après `RELANCE_JOURS`.


