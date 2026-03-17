import os
import re
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection

RAW_WORKSHEET = "Form Responses 1"  # Must exactly match the Google Sheets tab name
COLOR_ORDER = ["Vert", "Jaune", "Orange", "Rouge"]
DAYS_ORDER = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
COLOR_CARD_STYLES = {
    "Vert": ("#2ecc71", "#f0fdf4"),
    "Jaune": ("#f1c40f", "#fefce8"),
    "Orange": ("#e67e22", "#fff7ed"),
    "Rouge": ("#e74c3c", "#fef2f2"),
}

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="CERENE | Manager V42",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3 { color: #1e293b; font-family: 'Segoe UI', sans-serif; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #ffffff;
        border-radius: 6px 6px 0 0;
        font-weight: 600;
        border: 1px solid #e2e8f0;
        color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #fff;
        border-top: 3px solid #2563eb;
        color: #2563eb;
    }
    div[data-testid="stDataFrame"] { width: 100%; }
    .mistral-box {
        background: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 15px;
        border-radius: 6px;
        font-size: 0.9em;
        color: #14532d;
        margin-bottom: 20px;
        font-style: italic;
    }
    .alert-ln { background-color: #fefce8; border: 1px solid #eab308; color: #854d0e; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .alert-diego { background-color: #fef2f2; border: 1px solid #ef4444; color: #991b1b; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .priority-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #94a3b8;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .priority-card.urgence { border-left-color: #dc2626; background: #fef2f2; }
    .priority-card.vigilance-renforcee { border-left-color: #ea580c; background: #fff7ed; }
    .priority-card.a-surveiller { border-left-color: #ca8a04; background: #fefce8; }
    .priority-topline {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 10px;
        margin-bottom: 6px;
    }
    .priority-name { font-size: 1.02rem; font-weight: 700; color: #0f172a; }
    .priority-class { font-size: 0.86rem; color: #475569; font-weight: 600; }
    .priority-counts { font-size: 0.85rem; color: #334155; margin-bottom: 4px; }
    .priority-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }
    .priority-badge.urgence { background: #fee2e2; color: #991b1b; }
    .priority-badge.vigilance-renforcee { background: #ffedd5; color: #9a3412; }
    .priority-badge.a-surveiller { background: #fef9c3; color: #854d0e; }
    .vg-block-title { margin-bottom: 4px; }
    .vg-muted { color:#64748b; font-size:0.85rem; margin-bottom: 0.6rem; }
    .vg-positive-card {
        background: #f8fafc;
        border: 1px solid #dbeafe;
        border-left: 5px solid #16a34a;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }
    .vg-positive-name { font-size: 1rem; font-weight: 700; color: #14532d; }
    .vg-positive-meta { font-size: 0.84rem; color: #334155; }
    .vg-severe-note {
        padding: 8px 10px;
        border-radius: 8px;
        background: #fff7ed;
        border: 1px solid #fdba74;
        color: #9a3412;
        font-size: 0.84rem;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

USERS = st.secrets["users"]


def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if not st.session_state.password_correct:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            st.write("")
            with st.container(border=True):
                img_path = "VS Noel.jpeg"
                if os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                st.subheader("🔐 Connexion")
                user = st.text_input("Identifiant", key="u_in")
                pwd = st.text_input("Mot de passe", type="password", key="p_in")
                if st.button("Se connecter", type="primary", use_container_width=True):
                    if user.lower() in USERS and USERS[user.lower()] == pwd:
                        st.session_state.password_correct = True
                        st.session_state.real_user = user
                        st.rerun()
                    else:
                        st.error("Erreur d'identifiants.")
        return False
    return True


def load_raw_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    raw_df = conn.read(worksheet=RAW_WORKSHEET, ttl="30s")
    if raw_df is None or raw_df.empty:
        raise ValueError(
            f"La feuille '{RAW_WORKSHEET}' est vide, inaccessible ou mal configurée."
        )
    return raw_df


def detect_columns(df):
    columns = [str(c).strip() for c in df.columns]
    df.columns = columns

    def normalize(value):
        value = str(value).strip().lower()
        return (
            value.replace("é", "e")
            .replace("è", "e")
            .replace("ê", "e")
            .replace("ë", "e")
            .replace("à", "a")
            .replace("ù", "u")
            .replace("ô", "o")
            .replace("î", "i")
            .replace("ï", "i")
        )

    col_color = next((c for c in columns if "Couleur" in c or "Color" in c), None)
    col_eleve = next(
        (c for c in columns if "Élève" in c or "Eleve" in c or "Nom" in c), None
    )
    col_classe = next((c for c in columns if "Classe" in c or "Clase" in c), None)
    col_obs = next((c for c in columns if "Observation" in c or "Observacion" in c), None)

    adult_keywords = [
        "adulte",
        "prof",
        "adult",
        "enseignant",
        "teacher",
        "email",
        "e-mail",
        "adresse e-mail",
        "utilisateur",
        "nom de l'adulte",
        "nom du professeur",
    ]
    col_adult = next(
        (
            c
            for c in columns
            if any(k in normalize(c) for k in adult_keywords)
        ),
        None,
    )
    col_date = next(
        (
            c
            for c in columns
            if "Horodateur" in c or "Timestamp" in c or "Date" in c or c == "c"
        ),
        None,
    )

    if not col_date and len(columns) > 0:
        col_date = columns[0]

    required = [col_color, col_eleve, col_classe, col_date]
    if not all(required):
        raise ValueError(f"Colonnes manquantes. Trouvé: {columns}")

    return {
        "color": col_color,
        "eleve": col_eleve,
        "classe": col_classe,
        "obs": col_obs,
        "adult": col_adult,
        "date": col_date,
    }


def clean_data(df, cols):
    color_map = {
        "Vert": "Vert",
        "Verde": "Vert",
        "Jaune": "Jaune",
        "Amarillo": "Jaune",
        "Orange": "Orange",
        "Naranja": "Orange",
        "Rouge": "Rouge",
        "Rojo": "Rouge",
    }

    df = df.dropna(subset=[cols["eleve"], cols["date"], cols["color"]]).copy()
    df["Couleur_Clean"] = df[cols["color"]].map(color_map).fillna(df[cols["color"]])
    df["Date_Clean"] = pd.to_datetime(df[cols["date"]], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["Date_Clean"]).copy()
    return df


def get_p(d):
    if pd.isna(d):
        return "Hors"
    if d.month == 9 or (d.month == 10 and d.day <= 18):
        return "P1"
    if (d.month == 10 and d.day > 18) or d.month in [11, 12]:
        return "P2"
    return "P3+"


def apply_business_rules(df):
    days_map = {
        "Monday": "Lundi",
        "Tuesday": "Mardi",
        "Wednesday": "Mercredi",
        "Thursday": "Jeudi",
        "Friday": "Vendredi",
        "Saturday": "Samedi",
        "Sunday": "Dimanche",
    }

    df = df.copy()
    df["Semaine"] = df["Date_Clean"].dt.isocalendar().week
    df["Mois_Str"] = df["Date_Clean"].dt.strftime("%Y-%m")
    df["Semaine_Str"] = df["Date_Clean"].dt.strftime("%Y-W%V")
    df["Période"] = df["Date_Clean"].apply(get_p)
    df["Jour_Fr"] = df["Date_Clean"].dt.day_name().map(days_map)
    df["Heure"] = df["Date_Clean"].dt.hour
    return df


def render_sidebar(df):
    with st.sidebar:
        img_path = "VS Noel.jpeg"
        if os.path.exists(img_path):
            st.image(img_path, use_container_width=True)
        st.write("")
        u = st.session_state.get("real_user", "User")
        st.caption(f"Connecté: **{u.capitalize()}**")

        st.markdown(
            """
        <div class='mistral-box'>
        "Beaucoup de choses peuvent attendre, mais pas l'enfant... Son nom est Aujourd'hui."
        <br><b>- Gabriela Mistral</b>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.divider()
        st.caption(f"📄 Source: Google Sheets · Onglet `{RAW_WORKSHEET}`")
        st.caption("🔄 Données rafraîchies automatiquement toutes les 30 secondes.")
        if st.button("Actualiser maintenant", use_container_width=True):
            st.rerun()

        st.write("🔎 **Filtres Actifs**")
        all_p = sorted(df["Période"].dropna().astype(str).unique())
        if not all_p:
            st.warning("Aucune période détectée.")
            return df

        default_index = min(len(all_p) - 1, all_p.index("P2") if "P2" in all_p else len(all_p) - 1)
        sel_p = st.selectbox("Période", all_p, index=default_index, key="selected_period")
        df_p = df[df["Période"] == sel_p].copy()

        all_w = sorted(df_p["Semaine"].dropna().unique())
        sel_w = st.multiselect("Semaines", all_w, default=all_w, key="selected_weeks")
        if sel_w:
            df_f = df_p[df_p["Semaine"].isin(sel_w)].copy()
        else:
            df_f = df_p.copy()

        if st.button("Déconnexion"):
            st.session_state.password_correct = False
            st.rerun()

    return df_f


def apply_filters(df, selected_period, selected_weeks):
    if selected_period:
        df_period = df[df["Période"] == selected_period].copy()
    else:
        df_period = df.copy()

    if selected_weeks:
        return df_period[df_period["Semaine"].isin(selected_weeks)].copy()
    return df_period


def ensure_color_columns(pivot_df):
    for color in COLOR_ORDER:
        if color not in pivot_df.columns:
            pivot_df[color] = 0
    return pivot_df


def build_priority_students(df_f, col_eleve, col_classe, top_n=5):
    focus_df = df_f[df_f["Couleur_Clean"].isin(["Jaune", "Orange", "Rouge"])].copy()
    if focus_df.empty:
        return pd.DataFrame()

    latest_date = focus_df["Date_Clean"].max()
    weights = {"Rouge": 5.0, "Orange": 3.0, "Jaune": 1.5}

    days_since = (latest_date - focus_df["Date_Clean"]).dt.days.clip(lower=0)
    focus_df["Recency_Factor"] = 1 / (1 + (days_since / 14))
    focus_df["Weighted_Score"] = (
        focus_df["Couleur_Clean"].map(weights).fillna(0) * focus_df["Recency_Factor"]
    )

    counts = (
        focus_df.groupby([col_eleve, col_classe])["Couleur_Clean"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    counts = ensure_color_columns(counts)

    score_by_student = (
        focus_df.groupby([col_eleve, col_classe], as_index=False)["Weighted_Score"].sum()
    )
    last_obs = focus_df.groupby([col_eleve, col_classe], as_index=False)["Date_Clean"].max()

    ranked = counts.merge(score_by_student, on=[col_eleve, col_classe], how="left").merge(
        last_obs, on=[col_eleve, col_classe], how="left"
    )
    ranked = ranked.rename(columns={"Date_Clean": "Last_Observation"})
    ranked["Jaune_Bonus"] = (ranked["Jaune"] >= 3).astype(float) * 1.0
    ranked["Priority_Score"] = ranked["Weighted_Score"] + ranked["Jaune_Bonus"]

    ranked = ranked.sort_values(
        ["Priority_Score", "Rouge", "Orange", "Jaune", "Last_Observation"],
        ascending=[False, False, False, False, False],
    ).head(top_n)

    def vigilance_label(row):
        if row["Rouge"] >= 1 or row["Priority_Score"] >= 6:
            return "urgence"
        if row["Orange"] >= 2 or (row["Orange"] >= 1 and row["Jaune"] >= 2):
            return "vigilance renforcée"
        return "à surveiller"

    ranked["Vigilance_Label"] = ranked.apply(vigilance_label, axis=1)
    return ranked


def build_positive_signals(df_f, col_eleve, col_classe, top_n=5):
    if df_f.empty:
        return pd.DataFrame()

    latest_date = df_f["Date_Clean"].max()
    window_start = latest_date - pd.Timedelta(days=21)
    recent_df = df_f[df_f["Date_Clean"] >= window_start].copy()
    if recent_df.empty:
        return pd.DataFrame()

    summary = (
        recent_df.groupby([col_eleve, col_classe])["Couleur_Clean"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    summary = ensure_color_columns(summary)

    all_time = (
        df_f.groupby([col_eleve, col_classe])["Couleur_Clean"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )
    all_time = ensure_color_columns(all_time)
    all_time["Had_Past_Alerts"] = (all_time["Jaune"] + all_time["Orange"] + all_time["Rouge"]) > 0

    last_obs = recent_df.groupby([col_eleve, col_classe], as_index=False)["Date_Clean"].max()
    positive = summary.merge(all_time[[col_eleve, col_classe, "Had_Past_Alerts"]], on=[col_eleve, col_classe], how="left")
    positive = positive.merge(last_obs, on=[col_eleve, col_classe], how="left").rename(columns={"Date_Clean": "Last_Observation"})

    positive["Positive_Score"] = (
        positive["Vert"] * 2
        + (positive["Jaune"] == 0).astype(int) * 2
        + (positive["Orange"] == 0).astype(int) * 2
        + (positive["Rouge"] == 0).astype(int) * 3
        + positive["Had_Past_Alerts"].astype(int)
    )

    filtered = positive[
        (positive["Vert"] >= 3)
        | ((positive["Vert"] >= 2) & (positive["Orange"] == 0) & (positive["Rouge"] == 0))
    ].copy()
    if filtered.empty:
        return pd.DataFrame()

    def positive_label(row):
        if row["Vert"] >= 5 and row["Rouge"] == 0 and row["Orange"] == 0:
            return "dynamique positive"
        if row["Had_Past_Alerts"] and row["Vert"] >= 3 and row["Orange"] == 0 and row["Rouge"] == 0:
            return "amélioration notable"
        return "à encourager"

    filtered["Positive_Label"] = filtered.apply(positive_label, axis=1)
    return filtered.sort_values(
        ["Positive_Score", "Vert", "Last_Observation"],
        ascending=[False, False, False],
    ).head(top_n)


def format_weeks_context(weeks):
    if not weeks:
        return "Toutes les semaines disponibles"
    ordered_weeks = sorted(int(w) for w in weeks)
    return ", ".join([f"S{w}" for w in ordered_weeks])


def infer_trend(student_df):
    if len(student_df) < 6:
        return "Tendance non lisible (historique insuffisant)."

    severity_map = {"Vert": 0, "Jaune": 1, "Orange": 2, "Rouge": 3}
    scored = student_df.copy()
    scored["Severity"] = scored["Couleur_Clean"].map(severity_map).fillna(1)

    recent_avg = scored.tail(5)["Severity"].mean()
    previous_avg = scored.head(min(5, len(scored) - 1))["Severity"].mean()

    if recent_avg <= previous_avg - 0.4:
        return "Amélioration récente (couleurs globalement plus positives)."
    if recent_avg >= previous_avg + 0.4:
        return "Point de vigilance : dégradation récente observée."
    return "Tendance globalement stable sur la période sélectionnée."


def extract_keywords(observations):
    stopwords = {
        "le", "la", "les", "de", "des", "du", "un", "une", "et", "ou", "en", "dans", "sur", "avec",
        "pour", "pas", "plus", "mais", "que", "qui", "au", "aux", "ce", "cet", "cette", "a", "à", "est",
        "son", "sa", "ses", "elle", "il", "se", "ne", "d", "l", "tres", "très", "été", "etre", "être",
        "faire", "fait", "fois", "car", "comme", "tout", "tous", "toute", "toutes", "pendant", "apres", "après",
    }
    words = []
    for obs in observations:
        tokens = re.findall(r"[a-zA-Zàâçéèêëîïôûùüÿñæœ'-]{3,}", str(obs).lower())
        words.extend([w for w in tokens if w not in stopwords])
    return [w for w, _ in Counter(words).most_common(5)]


def build_student_summary_block(student_df, student_name, student_class, selected_period, selected_weeks, col_obs):
    counts = student_df["Couleur_Clean"].value_counts().reindex(COLOR_ORDER, fill_value=0)
    total = int(len(student_df))
    trend = infer_trend(student_df)

    obs_series = pd.Series(dtype=str)
    if col_obs is not None and col_obs in student_df.columns:
        obs_series = student_df[col_obs].dropna().astype(str)

    keywords = extract_keywords(obs_series.tolist()) if not obs_series.empty else []
    dominant_issues = ", ".join(keywords[:3]) if keywords else "Non identifié de manière fiable avec les observations actuelles."
    positive_points = "Présence d'observations vertes régulières." if counts["Vert"] > 0 else "Peu de points positifs explicites visibles dans les saisies."

    recent_rows = student_df.sort_values("Date_Clean", ascending=False).head(3)
    notable = []
    for _, row in recent_rows.iterrows():
        obs_text = ""
        if col_obs is not None and col_obs in row and pd.notna(row[col_obs]):
            obs_text = str(row[col_obs]).strip()
        if obs_text:
            notable.append(f"- {row['Date_Clean'].strftime('%d/%m')} · {row['Couleur_Clean']} · {obs_text}")
        else:
            notable.append(f"- {row['Date_Clean'].strftime('%d/%m')} · {row['Couleur_Clean']}")

    neutral_synthesis = (
        f"Sur la période sélectionnée, {student_name} présente {total} observation(s) "
        f"avec une répartition Vert/Jaune/Orange/Rouge de {counts['Vert']}/{counts['Jaune']}/{counts['Orange']}/{counts['Rouge']}. "
        f"{trend} Les observations invitent à poursuivre un accompagnement éducatif structuré, "
        f"en consolidant les points d'appui et en travaillant les situations récurrentes identifiées."
    )

    structured = {
        "Élève": student_name,
        "Classe": student_class,
        "Période": selected_period or "Non précisée",
        "Semaines": format_weeks_context(selected_weeks),
        "Total entrées": total,
        "Comptage couleurs": {color: int(counts[color]) for color in COLOR_ORDER},
        "Tendance": trend,
        "Points de vigilance récurrents (inférés)": dominant_issues,
        "Points positifs visibles": positive_points,
        "Dernières observations notables": "\n".join(notable) if notable else "Aucune observation notable disponible.",
        "Synthèse éducative neutre": neutral_synthesis,
    }

    prompt = (
        "À partir des éléments ci-dessous, rédige un profil pédagogique clair, humain et professionnel en français. "
        "Reste neutre, factuel et orienté accompagnement éducatif. "
        "Structure ta réponse en 4 parties : Forces, Vigilances, Évolution récente, Pistes d'action concrètes pour l'équipe.\n\n"
        f"{structured}"
    )

    return structured, prompt


def render_dashboard(df, df_f, cols):
    col_date = cols["date"]
    col_eleve = cols["eleve"]
    col_classe = cols["classe"]
    col_obs = cols["obs"]
    col_adult = cols["adult"]

    st.title("🎓 Pilotage Vie Scolaire")
    t1, t2, t3, t4, t5, t6, t7 = st.tabs(
        [
            "📊 Vue Globale",
            "🏫 Classes",
            "📋 Suivi",
            "⚖️ SANCTIONS",
            "🏆 HONNEUR",
            "👤 Dossier",
            "👥 Équipe",
        ]
    )

    with t1:
        k1, k2, k3, k4 = st.columns(4)
        tot = len(df_f)
        v = len(df_f[df_f["Couleur_Clean"] == "Vert"])
        j = len(df_f[df_f["Couleur_Clean"] == "Jaune"])
        inc = len(df_f[df_f["Couleur_Clean"].isin(["Rouge", "Orange"])])
        k1.metric("Total", tot)
        k2.metric("Verts", v, delta="Positif")
        k3.metric("Jaunes", j, delta_color="off")
        k4.metric("Incidents", inc, delta="-Alertes", delta_color="inverse")
        st.divider()

        col_priority, col_positive = st.columns(2)

        with col_priority:
            with st.container(border=True):
                st.subheader("🎯 Priorités du moment")
                st.caption(
                    "Classement basé sur les observations Jaune/Orange/Rouge du filtre actif, en privilégiant les signaux récents et sévères."
                )

                priority_df = build_priority_students(df_f, col_eleve, col_classe, top_n=5)
                if priority_df.empty:
                    st.info("Aucune observation Jaune, Orange ou Rouge dans le filtre actif.")
                else:
                    for _, row in priority_df.iterrows():
                        label = str(row["Vigilance_Label"])
                        label_css = (
                            label.replace(" ", "-")
                            .replace("é", "e")
                            .replace("à", "a")
                        )
                        last_obs = row["Last_Observation"].strftime("%d/%m/%Y") if pd.notna(row["Last_Observation"]) else "N/A"
                        st.markdown(
                            f"""
                            <div class='priority-card {label_css}'>
                                <div class='priority-topline'>
                                    <div>
                                        <div class='priority-name'>{row[col_eleve]}</div>
                                        <div class='priority-class'>Classe : {row[col_classe]}</div>
                                    </div>
                                    <span class='priority-badge {label_css}'>{label}</span>
                                </div>
                                <div class='priority-counts'>
                                    🔴 Rouge: <b>{int(row['Rouge'])}</b> &nbsp;•&nbsp;
                                    🟠 Orange: <b>{int(row['Orange'])}</b> &nbsp;•&nbsp;
                                    🟡 Jaune: <b>{int(row['Jaune'])}</b>
                                </div>
                                <div class='priority-class'>Dernière observation : {last_obs}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        with col_positive:
            with st.container(border=True):
                st.subheader("🌱 Signaux positifs / améliorations")
                st.caption("Élèves montrant une dynamique positive récente (sur les 3 dernières semaines disponibles).")

                positive_df = build_positive_signals(df_f, col_eleve, col_classe, top_n=5)
                if positive_df.empty:
                    st.info("Aucun signal positif marquant à afficher sur la fenêtre récente.")
                else:
                    for _, row in positive_df.iterrows():
                        last_obs = row["Last_Observation"].strftime("%d/%m/%Y") if pd.notna(row["Last_Observation"]) else "N/A"
                        st.markdown(
                            f"""
                            <div class='vg-positive-card'>
                                <div class='vg-positive-name'>{row[col_eleve]} · {row[col_classe]}</div>
                                <div class='vg-positive-meta'>
                                    🟢 Vert: <b>{int(row['Vert'])}</b> &nbsp;•&nbsp;
                                    🟡 Jaune: <b>{int(row['Jaune'])}</b> &nbsp;•&nbsp;
                                    🟠 Orange: <b>{int(row['Orange'])}</b> &nbsp;•&nbsp;
                                    🔴 Rouge: <b>{int(row['Rouge'])}</b><br>
                                    Dernière observation: {last_obs} &nbsp;•&nbsp; <b>{row['Positive_Label']}</b>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

        st.divider()
        c_pie, c_signals = st.columns([1, 2])
        with c_pie:
            st.subheader("Répartition")
            cts = df_f["Couleur_Clean"].value_counts()
            figp = px.pie(
                values=cts,
                names=cts.index,
                color=cts.index,
                color_discrete_map={
                    "Vert": "#2ecc71",
                    "Jaune": "#f1c40f",
                    "Orange": "#e67e22",
                    "Rouge": "#e74c3c",
                },
            )
            st.plotly_chart(figp, use_container_width=True)
        with c_signals:
            st.subheader("Lecture rapide")
            severe_recent = df_f[df_f["Couleur_Clean"].isin(["Orange", "Rouge"])].copy()
            severe_count = len(severe_recent)
            recurring_count = len(
                df_f[df_f["Couleur_Clean"] == "Jaune"]
                .groupby(col_eleve)
                .size()
                .loc[lambda x: x >= 3]
            )
            st.markdown(
                f"""
                <div class='vg-severe-note'>
                    <b>Signal immédiat :</b> {severe_count} observation(s) Orange/Rouge sur la période filtrée.<br>
                    <b>Signal récurrent :</b> {recurring_count} élève(s) avec au moins 3 observations Jaunes.
                </div>
                """,
                unsafe_allow_html=True,
            )

            recent_focus = (
                df_f.sort_values("Date_Clean", ascending=False)
                [["Date_Clean", col_eleve, col_classe, "Couleur_Clean"]]
                .head(8)
                .copy()
            )
            recent_focus["Date"] = recent_focus["Date_Clean"].dt.strftime("%d/%m/%Y")
            recent_focus["Signal"] = recent_focus["Couleur_Clean"].map(
                {
                    "Rouge": "🔴",
                    "Orange": "🟠",
                    "Jaune": "🟡",
                    "Vert": "🟢",
                }
            )
            st.dataframe(
                recent_focus[["Date", "Signal", col_eleve, col_classe, "Couleur_Clean"]],
                use_container_width=True,
                hide_index=True,
            )

        st.divider()
        st.subheader("🕒 Dernières observations")

        adult_label = None
        if col_adult is not None and col_adult in df_f.columns:
            adult_label = "Adulte / enseignant"
            df_f = df_f.copy()
            df_f[adult_label] = df_f[col_adult]

        history_columns = [
            col_date,
            col_eleve,
            col_classe,
            "Couleur_Clean",
            adult_label,
            col_obs,
        ]
        history_columns = [c for c in history_columns if c in df_f.columns and c is not None]

        latest_observations = df_f.sort_values("Date_Clean", ascending=False).head(5)
        latest_severe = df_f[df_f["Couleur_Clean"].isin(["Orange", "Rouge"])].sort_values(
            "Date_Clean", ascending=False
        ).head(3)

        c_latest, c_severe = st.columns(2)
        with c_latest:
            st.write("**5 dernières observations**")
            if latest_observations.empty:
                st.info("Aucune observation récente dans le filtre actif.")
            else:
                st.dataframe(latest_observations[history_columns], use_container_width=True, hide_index=True)

        with c_severe:
            st.write("**3 dernières observations graves**")
            if latest_severe.empty:
                st.info("Aucune observation Orange/Rouge sur la période filtrée.")
            else:
                st.dataframe(latest_severe[history_columns], use_container_width=True, hide_index=True)

    with t2:
        st.subheader("Analyse par Classe")
        df_class = (
            df_f.groupby([col_classe, "Couleur_Clean"]).size().unstack(fill_value=0)
        )
        df_class = ensure_color_columns(df_class)

        piv = df_f.groupby([col_eleve, col_classe])["Couleur_Clean"].value_counts().unstack(fill_value=0)
        piv = ensure_color_columns(piv)
        piv["Is_Incident"] = (piv["Orange"] >= 1) | (piv["Rouge"] >= 1)
        risk = piv.reset_index().groupby(col_classe)["Is_Incident"].sum()
        full_stats = df_class.join(risk).fillna(0)

        st.bar_chart(
            full_stats[["Vert", "Jaune", "Orange", "Rouge"]],
            color=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
        )

        if not full_stats.empty:
            st.divider()
            st.subheader("🏆 Podiums")
            c_best = full_stats["Vert"].idxmax()
            c_inc = (full_stats["Orange"] + full_stats["Rouge"]).idxmax()
            st.markdown(
                f"""
                <div style='display:flex; gap:20px;'>
                    <div style='background:#f0fdf4; padding:15px; border-radius:10px; border-left:4px solid #2ecc71; flex:1;'>
                        <small style='color:#2ecc71; font-weight:bold;'>CLASSE MODÈLE</small><br>
                        <span style='font-size:24px; font-weight:bold; color:#1e293b;'>{c_best}</span>
                    </div>
                    <div style='background:#fef2f2; padding:15px; border-radius:10px; border-left:4px solid #e74c3c; flex:1;'>
                        <small style='color:#e74c3c; font-weight:bold;'>PLUS D'INCIDENTS</small><br>
                        <span style='font-size:24px; font-weight:bold; color:#1e293b;'>{c_inc}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("#### Détails")
        st.dataframe(full_stats[["Vert", "Jaune", "Orange", "Rouge"]], use_container_width=True)

    with t3:
        st.subheader("📋 Listes de Suivi Éducatif")
        piv = df_f.groupby([col_eleve, col_classe])["Couleur_Clean"].value_counts().unstack(fill_value=0)
        piv = ensure_color_columns(piv)

        c_ln, c_d = st.columns(2)
        cond_accum = (piv["Jaune"] >= 3) & (piv["Orange"] == 0) & (piv["Rouge"] == 0)
        cond_aisle = (piv["Orange"] == 1) & (piv["Jaune"] == 0) & (piv["Rouge"] == 0)
        filter_ln = cond_accum | cond_aisle

        cond_red = piv["Rouge"] >= 1
        cond_org_yel = (piv["Orange"] >= 1) & (piv["Jaune"] >= 1)
        cond_multi_org = piv["Orange"] >= 2
        filter_d = cond_red | cond_org_yel | cond_multi_org

        with c_ln:
            st.markdown(
                '<div class="alert-ln"><b>👩‍🏫 Suivi LINDA & NELSON</b><br>• Accumulation Jaunes (≥3)<br>• 1 Orange "isolée" (sans jaunes)</div>',
                unsafe_allow_html=True,
            )
            st.dataframe(piv[filter_ln][["Orange", "Jaune"]], use_container_width=True)

        with c_d:
            st.markdown(
                '<div class="alert-diego"><b>👨‍🏫 Suivi DIEGO</b><br>• Incidents (Rouge)<br>• Orange + Jaune<br>• Récidive Orange (≥2)</div>',
                unsafe_allow_html=True,
            )
            st.dataframe(
                piv[filter_d][["Rouge", "Orange", "Jaune"]], use_container_width=True
            )

    with t4:
        st.markdown('<h3 style="color:#b91c1c;">⚖️ SANCTIONS & RETENUES</h3>', unsafe_allow_html=True)
        piv_sanc = (
            df_f.groupby([col_eleve, col_classe])["Couleur_Clean"].value_counts().unstack(fill_value=0)
        )
        piv_sanc = ensure_color_columns(piv_sanc)
        piv_sanc["Oranges_Virtuelles"] = piv_sanc["Orange"] + (piv_sanc["Jaune"] // 3)
        filter_r = piv_sanc["Oranges_Virtuelles"] >= 2
        df_r = piv_sanc[filter_r][["Oranges_Virtuelles", "Rouge", "Orange", "Jaune"]].sort_values(
            "Oranges_Virtuelles", ascending=False
        )

        c1, c2 = st.columns([1, 2])
        with c1:
            st.info("ℹ️ **Règle :** 2 Oranges (ou équivalent) = 1 Retenue.")
            if not df_r.empty:
                st.metric("Élèves en Retenue", len(df_r), delta="Action requise", delta_color="inverse")
            else:
                st.metric("Retenues", 0)
        with c2:
            if not df_r.empty:
                st.dataframe(df_r, use_container_width=True)
            else:
                st.success("Aucune retenue.")

    with t5:
        st.subheader("🏆 Tableau d'Honneur")
        st.markdown(
            """
            **Critères d'Excellence :**
            * 👍 **+1** par Vert
            * ⚠️ **-1** par Jaune
            * 🚨 **-2** par Orange
            * ⛔ **Disqualifié** si Rouge > 0 ou moins de 2 Verts.
            """
        )

        piv_hon = (
            df_f.groupby([col_eleve, col_classe])["Couleur_Clean"].value_counts().unstack(fill_value=0)
        )
        piv_hon = ensure_color_columns(piv_hon)

        honors = []
        for idx, row in piv_hon.iterrows():
            if row["Rouge"] > 0 or row["Vert"] < 2:
                score = -999
            else:
                score = (row["Vert"] * 1) + (row["Jaune"] * -1) + (row["Orange"] * -2)
            honors.append({"Élève": idx[0], "Classe": idx[1], "Score": score, "Verts": row["Vert"]})

        df_hon = pd.DataFrame(honors)
        if not df_hon.empty:
            df_winners = df_hon[df_hon["Score"] > 0].sort_values(["Score", "Verts"], ascending=False)
            st.write("#### 🥇 Premiers de Classe")
            top_per_class = df_winners.loc[df_winners.groupby("Classe")["Score"].idxmax()]
            st.dataframe(top_per_class.set_index("Classe"), use_container_width=True)
            st.write("#### 📜 Liste Complète")
            st.dataframe(df_winners, use_container_width=True)
        else:
            st.info("Pas encore de données suffisantes.")

    with t6:
        st.subheader("👤 Dossier & Évolution")
        eleves = sorted(df[col_eleve].astype(str).unique())
        sel_eleve = st.selectbox("Rechercher un élève", eleves)

        selected_period = st.session_state.get("selected_period")
        selected_weeks = st.session_state.get("selected_weeks", [])

        de_filtered = df_f[df_f[col_eleve] == sel_eleve].copy().sort_values("Date_Clean", ascending=True)
        de_full = df[df[col_eleve] == sel_eleve].copy().sort_values("Date_Clean", ascending=True)

        if de_filtered.empty:
            st.info("Aucune observation pour cet élève sur les filtres actuellement sélectionnés.")
        else:
            selected_class = str(de_filtered[col_classe].dropna().astype(str).mode().iloc[0]) if col_classe in de_filtered.columns and not de_filtered[col_classe].dropna().empty else "Non renseignée"
            color_counts = de_filtered["Couleur_Clean"].value_counts().reindex(COLOR_ORDER, fill_value=0)

            st.markdown("**Synthèse rapide par couleur (période/semaines sélectionnées)**")
            cards = st.columns(4)
            for idx, color in enumerate(COLOR_ORDER):
                border_color, bg_color = COLOR_CARD_STYLES[color]
                cards[idx].markdown(
                    f"""
                    <div style='background:{bg_color}; border:1px solid {border_color}; border-radius:10px; padding:10px 12px;'>
                        <div style='font-size:0.8rem; color:#475569; text-transform:uppercase; letter-spacing:0.4px;'>{color}</div>
                        <div style='font-size:1.6rem; font-weight:700; color:#0f172a;'>{int(color_counts[color])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            c_evol, c_hist = st.columns([1, 2])
            with c_evol:
                st.metric("Total Entrées (filtres actifs)", len(de_filtered))
                dom_mois = de_full.groupby("Mois_Str")["Couleur_Clean"].agg(lambda x: x.mode().iloc[0])
                st.write("**Dominante par Mois:**")
                st.dataframe(dom_mois, use_container_width=True)
            with c_hist:
                evol = de_full.groupby(["Semaine_Str", "Couleur_Clean"]).size().reset_index(name="Count")
                fig = px.bar(
                    evol,
                    x="Semaine_Str",
                    y="Count",
                    color="Couleur_Clean",
                    title="Évolution Hebdomadaire",
                    color_discrete_map={
                        "Vert": "#2ecc71",
                        "Jaune": "#f1c40f",
                        "Orange": "#e67e22",
                        "Rouge": "#e74c3c",
                    },
                )
                st.plotly_chart(fig, use_container_width=True)

                st.write("**Historique**")
                adult_label = None
                if col_adult is not None and col_adult in de_full.columns:
                    adult_label = "Adulte / enseignant"
                    de_full[adult_label] = de_full[col_adult]

                cols_show = [col_date, "Heure", "Couleur_Clean", adult_label, col_obs]
                cols_final = [c for c in cols_show if c in de_full.columns and c is not None]
                st.dataframe(
                    de_full.sort_values("Date_Clean", ascending=False)[cols_final],
                    use_container_width=True,
                )

            st.divider()
            st.markdown("### 🧾 Résumé prêt à exploiter")
            st.caption("Bloc copiable pour préparer une analyse humaine assistée par IA (sans connexion API).")
            structured_summary, prompt_text = build_student_summary_block(
                de_filtered,
                sel_eleve,
                selected_class,
                selected_period,
                selected_weeks,
                col_obs,
            )

            st.markdown("**Synthèse prête pour IA**")
            st.code(str(structured_summary), language="text")
            st.markdown("**Prompt recommandé (copier/coller)**")
            st.code(prompt_text, language="text")

    with t7:
        st.subheader("👥 Équipe éducative")
        st.caption("Répartition des observations par adulte / enseignant.")

        if col_adult is not None and col_adult in df.columns:
            c1, c2 = st.columns([1, 3], gap="large")
            with c1:
                sel_p = st.selectbox("Professeur", ["Global"] + sorted(df_f[col_adult].astype(str).unique()))
            with c2:
                if sel_p == "Global":
                    fig = px.histogram(
                        df_f,
                        x=col_adult,
                        color="Couleur_Clean",
                        barmode="stack",
                        color_discrete_map={
                            "Vert": "#2ecc71",
                            "Jaune": "#f1c40f",
                            "Orange": "#e67e22",
                            "Rouge": "#e74c3c",
                        },
                    )
                else:
                    sub = df_f[df_f[col_adult] == sel_p]
                    fig = px.histogram(
                        sub,
                        x="Jour_Fr",
                        color="Couleur_Clean",
                        category_orders={"Jour_Fr": DAYS_ORDER},
                        color_discrete_map={
                            "Vert": "#2ecc71",
                            "Jaune": "#f1c40f",
                            "Orange": "#e67e22",
                            "Rouge": "#e74c3c",
                        },
                    )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Aucune colonne adulte/enseignant détectée dans la source actuelle. "
                "L'onglet Équipe reste disponible, mais les graphiques ne peuvent pas être affichés."
            )


@st.fragment(run_every="30s")
def render_dashboard_fragment(selected_period, selected_weeks):
    try:
        bootstrap_data = st.session_state.pop("bootstrap_data", None)
        if bootstrap_data is not None:
            df, cols = bootstrap_data
        else:
            raw_df = load_raw_data()
            cols = detect_columns(raw_df)
            cleaned_df = clean_data(raw_df, cols)
            df = apply_business_rules(cleaned_df)

        if df.empty:
            st.title("🎓 Pilotage Vie Scolaire")
            st.warning("Aucune donnée exploitable après nettoyage.")
            return

        df_f = apply_filters(df, selected_period, selected_weeks)
        if df_f.empty:
            st.title("🎓 Pilotage Vie Scolaire")
            st.info("Aucune donnée disponible pour les filtres sélectionnés.")
            return

        render_dashboard(df, df_f, cols)

    except Exception as e:
        st.title("🎓 Pilotage Vie Scolaire")
        st.error(
            "Impossible de charger les données Google Sheets. Vérifiez le nom de l'onglet, "
            "les permissions du document et les secrets Streamlit."
        )
        st.exception(e)


if check_password():
    try:
        base_raw = load_raw_data()
        base_cols = detect_columns(base_raw)
        base_clean = clean_data(base_raw, base_cols)
        base_df = apply_business_rules(base_clean)
        st.session_state["bootstrap_data"] = (base_df, base_cols)

        filtered_df = render_sidebar(base_df)
        selected_period = st.session_state.get("selected_period")
        if selected_period is None and not filtered_df.empty:
            selected_period = filtered_df["Période"].iloc[0]
        selected_weeks = st.session_state.get("selected_weeks", [])

        render_dashboard_fragment(selected_period, selected_weeks)

    except Exception as e:
        st.title("🎓 Pilotage Vie Scolaire")
        st.error(
            "Impossible de charger les données Google Sheets. Vérifiez le nom de l'onglet, "
            "les permissions du document et les secrets Streamlit."
        )
        st.exception(e)
