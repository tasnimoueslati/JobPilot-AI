import os
from datetime import date
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()
_c = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
T = "candidatures"
STATUTS = ["À postuler", "Postulé", "Entretien planifié", "En attente de réponse", "Accepté", "Refusé", "Abandonné"]

def add(raw_text, source="manuel"):
    return _c.table(T).insert({"raw_text": raw_text, "source": source}).execute().data[0]

def all_():
    return _c.table(T).select("*").order("created_at", desc=True).execute().data

def update(id_, **fields):
    if fields.get("statut") == "Postulé":
        fields.setdefault("date_postule", date.today().isoformat())
    return _c.table(T).update(fields).eq("id", id_).execute()

def delete(id_):
    return _c.table(T).delete().eq("id", id_).execute()

def delete_many(ids):
    return _c.table(T).delete().in_("id", list(ids)).execute() if ids else None
