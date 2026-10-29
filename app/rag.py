"""RAG sur Supabase Vector (pgvector) : le CV est découpé, vectorisé (FastEmbed, local)
puis stocké dans la table cv_chunks ; la recherche passe par la fonction SQL match_cv_chunks."""
from dataclasses import dataclass
from fastembed import TextEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from .db import _c   # client Supabase partagé

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 384 dims, FR/EN
_emb = TextEmbedding(MODEL)

@dataclass
class CVStore:
    name: str

def _embed(texts):
    return [v.tolist() for v in _emb.embed(texts)]

def pdf_to_text(file) -> str:
    return "\n".join(p.extract_text() or "" for p in PdfReader(file).pages)

def build_cv_store(cv_text: str, cv_name: str) -> CVStore:
    chunks = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=60).split_text(cv_text)
    _c.table("cv_chunks").delete().eq("cv_name", cv_name).execute()   # ré-indexation propre
    rows = [{"cv_name": cv_name, "content": t, "embedding": e} for t, e in zip(chunks, _embed(chunks))]
    _c.table("cv_chunks").insert(rows).execute()
    return CVStore(cv_name)

def cv_context(store: CVStore, query: str, k=5) -> str:
    res = _c.rpc("match_cv_chunks", {"query_embedding": _embed([query])[0],
                                      "p_cv_name": store.name, "match_count": k}).execute()
    return "\n---\n".join(r["content"] for r in res.data)

def list_cvs() -> list[str]:
    """Noms des CV déjà indexés dans Supabase."""
    rows = _c.table("cv_chunks").select("cv_name").limit(10000).execute().data
    return sorted({r["cv_name"] for r in rows})

def delete_cv(name: str):
    """Supprime tous les morceaux d'un CV (RGPD : droit à l'effacement)."""
    _c.table("cv_chunks").delete().eq("cv_name", name).execute()
