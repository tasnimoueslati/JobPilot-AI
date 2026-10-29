"""Système multi-agents LangGraph.
Coordinateur = le graphe : offre -> matching -> (lettre || entretien) -> fin."""
import os, json, re
from typing import TypedDict, Any
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from .rag import cv_context
load_dotenv()

llm = ChatGroq(model=os.getenv("GROQ_MODEL", "gpt-oss-120b"), temperature=0.3)

class State(TypedDict, total=False):
    raw_offer: str
    cv_store: Any
    offre: dict
    matching: dict
    lettre: str
    entretien: dict

def _json(prompt: str) -> dict:
    out = llm.invoke(prompt + "\n\nRéponds UNIQUEMENT avec un JSON valide, sans texte autour.").content
    m = re.search(r"\{.*\}", out, re.S)
    return json.loads(m.group(0)) if m else {}

def agent_offre(s: State):
    return {"offre": _json(f"""Extrais de cette offre d'emploi un JSON avec les clés :
titre, entreprise, localisation, type_contrat, competences_requises (liste),
competences_souhaitees (liste), experience, missions (liste), avantages (liste).
Mets null si absent.\n\nOFFRE:\n{s['raw_offer']}""")}

def agent_matching(s: State):
    ctx = cv_context(s["cv_store"], json.dumps(s["offre"], ensure_ascii=False))
    return {"matching": _json(f"""Compare ce profil (extraits du CV) à l'offre.
Retourne un JSON : score (0-100 entier), forces (liste), ecarts (liste),
suggestions_cv (liste d'actions concrètes et actionnables).
Sois honnête, n'invente aucune expérience.\n\nOFFRE:\n{json.dumps(s['offre'], ensure_ascii=False)}\n\nCV:\n{ctx}""")}

def agent_lettre(s: State):
    ctx = cv_context(s["cv_store"], s["raw_offer"][:1500], k=6)
    return {"lettre": llm.invoke(f"""Rédige en français une lettre de motivation (250-300 mots),
professionnelle et personnalisée, pour cette offre. Appuie-toi uniquement sur les faits du CV.
Points forts à valoriser : {s['matching'].get('forces')}\n\nOFFRE:\n{json.dumps(s['offre'], ensure_ascii=False)}\n\nCV:\n{ctx}""").content}

def agent_entretien(s: State):
    ctx = cv_context(s["cv_store"], s["raw_offer"][:1500], k=6)
    return {"entretien": _json(f"""Prépare l'entretien. JSON : questions = liste de 8 objets
{{question, type (technique|comportemental|motivation), reponse_suggeree (méthode STAR si pertinent, basée sur le CV)}},
et conseils (liste de 3).\n\nOFFRE:\n{json.dumps(s['offre'], ensure_ascii=False)}\n\nCV:\n{ctx}""")}

g = StateGraph(State)
g.add_node("offre", agent_offre); g.add_node("matching", agent_matching)
g.add_node("lettre", agent_lettre); g.add_node("entretien", agent_entretien)
g.set_entry_point("offre")
g.add_edge("offre", "matching")
g.add_edge("matching", "lettre"); g.add_edge("matching", "entretien")
g.add_edge("lettre", END); g.add_edge("entretien", END)
graph = g.compile()

def analyser(raw_offer: str, cv_store) -> State:
    return graph.invoke({"raw_offer": raw_offer, "cv_store": cv_store})
