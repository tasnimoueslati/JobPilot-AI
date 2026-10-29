"""Agent Suivi & Notifications : 4 règles de rappel (Telegram), sans doublons.
 1. Relance après X jours (avec brouillon de message généré)
 2. Veille d'entretien (résumé de préparation)
 3. Remerciement 3 jours après l'entretien
 4. Résumé hebdomadaire (le lundi)"""
import os, requests
from datetime import date, timedelta
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from . import db
load_dotenv()
_llm = None

def llm():
    global _llm
    _llm = _llm or ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), temperature=0.4)
    return _llm

def telegram(msg: str):
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (t and c): print("[Telegram non configuré]", msg); return
    requests.post(f"https://api.telegram.org/bot{t}/sendMessage", json={"chat_id": c, "text": msg[:4000]}, timeout=10)

def _done(c, key):  return key in (c.get("rappels") or {})
def _mark(c, key):  db.update(c["id"], rappels={**(c.get("rappels") or {}), key: date.today().isoformat()})
def _d(v):          return date.fromisoformat(v[:10]) if v else None

def _brouillon(c) -> str:
    return llm().invoke(f"""Rédige en français un court email de relance (80 mots max), poli et non insistant,
pour la candidature « {c.get('titre')} » chez {c.get('entreprise')}, envoyée le {c.get('date_postule')}.
Termine par une formule de politesse. Ne mets pas de placeholder inutile.""").content

def relances(rows, today):
    n, seuil = 0, int(os.getenv("RELANCE_JOURS", 7))
    for c in rows:
        ref = _d(c.get("derniere_relance")) or _d(c.get("date_postule"))
        if c["statut"] == "Postulé" and ref and (today - ref).days >= seuil:
            b = _brouillon(c)
            db.update(c["id"], relance_brouillon=b, derniere_relance=today.isoformat())
            telegram(f"⏰ Pas de réponse : {c['titre']} @ {c['entreprise']}\n\nBrouillon de relance :\n{b}"); n += 1
    return n

def veille_entretien(rows, today):
    n = 0
    for c in rows:
        d = _d(c.get("date_entretien"))
        if c["statut"] == "Entretien planifié" and d == today + timedelta(days=1) and not _done(c, "veille"):
            e = c.get("entretien") or {}
            qs = "\n".join(f"• {q.get('question')}" for q in e.get("questions", [])[:5])
            telegram(f"🎤 Entretien demain : {c['titre']} @ {c['entreprise']} ({c['date_entretien'][11:16]})\n\nQuestions clés :\n{qs}\n\nConseils : {' · '.join(e.get('conseils', []))}")
            _mark(c, "veille"); n += 1
    return n

def remerciements(rows, today):
    n = 0
    for c in rows:
        d = _d(c.get("date_entretien"))
        if c["statut"] in ("Entretien planifié", "En attente de réponse") and d and (today - d).days >= 3 and not _done(c, "merci"):
            telegram(f"🙏 N'oublie pas l'email de remerciement : {c['titre']} @ {c['entreprise']} (entretien du {d})")
            _mark(c, "merci"); n += 1
    return n

def resume_hebdo(rows, today):
    if today.weekday() != 0: return 0
    cnt = lambda s: sum(c["statut"] == s for c in rows)
    prochains = [c for c in rows if c["statut"] == "Entretien planifié" and (_d(c.get("date_entretien")) or date.min) >= today]
    telegram(f"📊 Résumé de la semaine\n• À postuler : {cnt('À postuler')}\n• Postulé : {cnt('Postulé')}\n"
             f"• Entretiens planifiés : {len(prochains)}\n• En attente de réponse : {cnt('En attente de réponse')}\n"
             f"• Acceptées : {cnt('Accepté')} · Refusées : {cnt('Refusé')}"); return 1

def run_all() -> int:
    rows, today = [c for c in db.all_() if c.get("offre")], date.today()
    return sum(f(rows, today) for f in (relances, veille_entretien, remerciements, resume_hebdo))

if __name__ == "__main__":
    print(run_all(), "notification(s) envoyée(s)")
