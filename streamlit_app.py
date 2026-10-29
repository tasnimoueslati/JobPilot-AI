import html
import streamlit as st, pandas as pd
from datetime import date, time, datetime
from app import db, agents, rag, notifier

st.set_page_config(page_title="JobPilot AI", page_icon="🧭", layout="wide")
NEW = "➕ Ajouter un nouveau CV"
COL = {"À postuler": "#64748b", "Postulé": "#3b82f6", "Entretien planifié": "#8b5cf6",
       "En attente de réponse": "#f59e0b", "Accepté": "#10b981", "Refusé": "#ef4444", "Abandonné": "#94a3b8"}

st.markdown("""<style>
.block-container{padding-top:2rem;max-width:1500px}
[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.25);border-radius:14px;padding:14px 18px;background:rgba(128,128,128,.06)}
[data-testid="stMetricLabel"]{opacity:.7}
.hero{padding:6px 0 18px}.hero h1{margin:0;font-size:2rem}.hero p{margin:2px 0 0;opacity:.65}
.board{display:flex;gap:14px;overflow-x:auto;padding-bottom:10px}
.lane{min-width:215px;flex:1;background:rgba(128,128,128,.07);border-radius:14px;padding:10px}
.lane h4{margin:2px 4px 10px;font-size:.85rem;display:flex;justify-content:space-between;align-items:center}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
.cnt{background:rgba(128,128,128,.22);border-radius:10px;padding:0 8px;font-size:.75rem}
.card{border:1px solid rgba(128,128,128,.22);border-left:4px solid var(--c);border-radius:10px;padding:10px 12px;margin-bottom:9px;background:rgba(255,255,255,.04)}
.card b{font-size:.9rem}.card small{display:block;opacity:.65;margin-top:2px}
.badge{display:inline-block;margin-top:7px;padding:1px 9px;border-radius:12px;font-size:.75rem;font-weight:600;color:#fff}
.empty{opacity:.4;font-size:.8rem;text-align:center;padding:12px 0}
</style>""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🧭 JobPilot AI</h1><p>Suivi de candidatures et préparation d\'entretiens</p></div>', unsafe_allow_html=True)

def save_result(id_, r):
    o = r["offre"]
    db.update(id_, offre=o, matching=r["matching"], lettre=r["lettre"], entretien=r["entretien"],
              titre=o.get("titre"), entreprise=o.get("entreprise"),
              localisation=o.get("localisation"), contrat=o.get("type_contrat"))

def score_color(s):
    return "#10b981" if isinstance(s, (int, float)) and s >= 75 else "#f59e0b" if isinstance(s, (int, float)) and s >= 50 else "#ef4444"

# ---------- Sidebar : CV ----------
with st.sidebar:
    st.header("Mon CV")
    cvs = rag.list_cvs()
    options = cvs + [NEW]
    if st.session_state.get("cv_choice") not in options: st.session_state.pop("cv_choice", None)
    choice = st.selectbox("CV actif", options, key="cv_choice")
    if choice == NEW:
        st.session_state.pop("cv_store", None)
        cv = st.file_uploader("CV (PDF)", type="pdf")
        if cv:
            with st.spinner("Indexation du CV…"): rag.build_cv_store(rag.pdf_to_text(cv), cv.name)
            st.session_state.cv_choice = cv.name; st.rerun()
        st.info("Charge un CV pour commencer")
    else:
        st.session_state.cv_store = rag.CVStore(choice)
        st.success("CV indexé ✅")
        if st.session_state.get("confirm_del") == choice:
            st.warning("Supprimer définitivement ce CV ?")
            c1, c2 = st.columns(2)
            if c1.button("Oui, supprimer"):
                rag.delete_cv(choice)
                for k in ("cv_choice", "cv_store", "confirm_del"): st.session_state.pop(k, None)
                st.rerun()
            if c2.button("Annuler"): st.session_state.pop("confirm_del"); st.rerun()
        elif st.button("🗑️ Supprimer ce CV"): st.session_state.confirm_del = choice; st.rerun()
    st.divider()
    if st.button("🔔 Lancer les rappels"): st.write(notifier.run_all(), "notification(s) envoyée(s)")

has_cv = "cv_store" in st.session_state
rows = db.all_()
data = [c for c in rows if c.get("offre")]
tab_board, tab_detail, tab_add = st.tabs(["📊 Dashboard", "📂 Détail & préparation", "➕ Nouvelle offre"])

# ---------- Dashboard ----------
with tab_board:
    suivies = [c for c in data if c["statut"] != "À postuler"]
    repondu = [c for c in suivies if c["statut"] not in ("Postulé", "Abandonné")]
    scores = [(c["matching"] or {}).get("score") for c in data if isinstance((c["matching"] or {}).get("score"), (int, float))]
    k = st.columns(5)
    k[0].metric("Candidatures", len(data))
    k[1].metric("En cours", sum(c["statut"] in ("Postulé", "Entretien planifié", "En attente de réponse") for c in data))
    k[2].metric("Entretiens planifiés", sum(c["statut"] == "Entretien planifié" for c in data))
    k[3].metric("Taux de réponse", f"{round(100 * len(repondu) / len(suivies))} %" if suivies else "–")
    k[4].metric("Score moyen", f"{round(sum(scores) / len(scores))}/100" if scores else "–")
    st.write("")
    lanes = ""
    for s in db.STATUTS:
        items = [c for c in data if c["statut"] == s]
        cards = ""
        for c in items:
            sc = (c["matching"] or {}).get("score")
            when = f"<small>📅 {c['date_entretien'][:10]} {c['date_entretien'][11:16]}</small>" if c.get("date_entretien") else ""
            cards += (f'<div class="card" style="--c:{COL[s]}"><b>{html.escape(str(c["titre"]))}</b>'
                      f'<small>{html.escape(str(c["entreprise"]))}</small>{when}'
                      f'<span class="badge" style="background:{score_color(sc)}">{sc if sc is not None else "?"}/100</span></div>')
        lanes += (f'<div class="lane"><h4><span><span class="dot" style="background:{COL[s]}"></span>{s}</span>'
                  f'<span class="cnt">{len(items)}</span></h4>{cards or "<div class=empty>Aucune</div>"}</div>')
    st.markdown(f'<div class="board">{lanes}</div>', unsafe_allow_html=True)
    if data:
        a, b = st.columns([3, 2])
        with a:
            st.subheader("Toutes les candidatures")
            st.dataframe(pd.DataFrame([{"Poste": c["titre"], "Entreprise": c["entreprise"], "Contrat": c["contrat"],
                "Score": (c["matching"] or {}).get("score"), "Statut": c["statut"],
                "Entretien": (c.get("date_entretien") or "")[:16].replace("T", " ")} for c in data]),
                use_container_width=True, hide_index=True,
                column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")})
        with b:
            st.subheader("Répartition")
            st.bar_chart(pd.Series({s: sum(c["statut"] == s for c in data) for s in db.STATUTS}))

# ---------- Détail ----------
with tab_detail:
    if not data: st.info("Aucune candidature analysée.")
    else:
        c = st.selectbox("Candidature", data, format_func=lambda x: f"{x['titre']} — {x['entreprise']}")
        r1, r2 = st.columns([2, 1])
        new = r1.selectbox("Statut", db.STATUTS, index=db.STATUTS.index(c["statut"]) if c["statut"] in db.STATUTS else 0)
        if new != c["statut"]: db.update(c["id"], statut=new); st.rerun()
        r2.metric("Compatibilité", f"{(c['matching'] or {}).get('score', '?')}/100")
        cur = c.get("date_entretien")
        e1, e2, e3 = st.columns([2, 1, 1])
        d = e1.date_input("Date d'entretien", value=date.fromisoformat(cur[:10]) if cur else None)
        t = e2.time_input("Heure", value=time.fromisoformat(cur[11:16]) if cur else time(10, 0))
        e3.write(""); e3.write("")
        if e3.button("Enregistrer la date") and d:
            db.update(c["id"], date_entretien=datetime.combine(d, t).isoformat(), statut="Entretien planifié", rappels={})
            st.rerun()
        m = c["matching"] or {}
        a, b = st.columns(2)
        a.markdown("**✅ Points forts**\n" + "\n".join(f"- {x}" for x in m.get("forces", [])))
        b.markdown("**⚠️ Écarts**\n" + "\n".join(f"- {x}" for x in m.get("ecarts", [])))
        st.markdown("**🛠️ Suggestions pour le CV**\n" + "\n".join(f"- {x}" for x in m.get("suggestions_cv", [])))
        with st.expander("✉️ Lettre de motivation"):
            st.text_area("Lettre", c["lettre"], height=350, key=f"l{c['id']}", label_visibility="collapsed")
        with st.expander("🎤 Préparation d'entretien"):
            e = c["entretien"] or {}
            for q in e.get("questions", []): st.markdown(f"**[{q.get('type')}] {q.get('question')}**\n\n{q.get('reponse_suggeree')}")
            st.markdown("**Conseils :** " + " · ".join(e.get("conseils", [])))
        if c.get("relance_brouillon"):
            with st.expander("📨 Dernier brouillon de relance"): st.code(c["relance_brouillon"], language=None)
        notes = st.text_area("📝 Notes d'entretien", c.get("notes") or "", key=f"n{c['id']}")
        n1, n2 = st.columns([1, 5])
        if n1.button("Enregistrer les notes"): db.update(c["id"], notes=notes); st.toast("Notes sauvegardées")
        if n2.button("🗑️ Supprimer cette candidature"): db.delete(c["id"]); st.rerun()

# ---------- Nouvelle offre ----------
with tab_add:
    txt = st.text_area("Colle l'offre d'emploi", height=250)
    pdf = st.file_uploader("…ou upload PDF", type="pdf", key="offre_pdf")
    if st.button("Analyser", type="primary"):
        raw = rag.pdf_to_text(pdf) if pdf else txt
        if not raw.strip() or not has_cv: st.error("Il faut une offre et un CV actif.")
        else:
            try:
                with st.spinner("Les agents travaillent… (offre → matching → lettre → entretien)"):
                    res = agents.analyser(raw, st.session_state.cv_store)
                    save_result(db.add(raw)["id"], res)
                st.success(f"Score de compatibilité : {res['matching'].get('score')}/100")
            except Exception as ex: st.error(f"Analyse échouée, rien n'a été enregistré : {ex}")
    pending = [c for c in rows if not c.get("offre")]
    mails = [c for c in pending if c["source"] == "email"]
    failed = [c for c in pending if c["source"] != "email"]
    if mails:
        st.subheader(f"📬 {len(mails)} offre(s) reçue(s) par email")
        if st.button("Analyser les offres en attente", disabled=not has_cv):
            for c in mails:
                try: save_result(c["id"], agents.analyser(c["raw_text"], st.session_state.cv_store))
                except Exception as ex: st.error(f"Offre {c['id']} : {ex}")
            st.rerun()
    if failed:
        st.warning(f"🧹 {len(failed)} offre(s) non analysée(s).")
        if st.button("Supprimer ces offres"): db.delete_many(c["id"] for c in failed); st.rerun()
