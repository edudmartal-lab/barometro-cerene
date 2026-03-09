import os
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection

RAW_WORKSHEET = "Form Responses 1"  # Must exactly match the Google Sheets tab name
COLOR_ORDER = ["Vert", "Jaune", "Orange", "Rouge"]
DAYS_ORDER = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]

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

    .obs-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #cbd5e1;
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 10px;
    }
    .obs-card.severe {
        border-width: 1px;
        border-left-width: 5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .obs-meta {
        font-size: 0.82rem;
        color: #475569;
        margin-bottom: 6px;
    }
    .obs-main {
        font-size: 0.92rem;
        color: #0f172a;
        line-height: 1.35;
    }
    .obs-note {
        margin-top: 6px;
        font-size: 0.88rem;
        color: #334155;
    }
    .obs-badge {
        display: inline-block;
        margin-left: 8px;
        padding: 1px 8px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid transparent;
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

    col_color = next((c for c in columns if "Couleur" in c or "Color" in c), None)
    col_eleve = next(
        (c for c in columns if "Élève" in c or "Eleve" in c or "Nom" in c), None
    )
    col_classe = next((c for c in columns if "Classe" in c or "Clase" in c), None)
    col_obs = next((c for c in columns if "Observation" in c or "Observacion" in c), None)
    col_adult = next(
        (c for c in columns if "Adulte" in c or "Prof" in c or "Adult" in c), "Adulte"
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


def truncate_text(value, max_len=140):
    if value is None or pd.isna(value):
        return ""
    txt = str(value).strip()
    if len(txt) <= max_len:
        return txt
    return txt[: max_len - 1].rstrip() + "…"


def render_observation_cards(data, cols, title, severe_only=False, limit=5):
    st.subheader(title)
    if data.empty:
        st.info("Aucune observation disponible pour les filtres sélectionnés.")
        return

    view = data.copy()
    if severe_only:
        view = view[view["Couleur_Clean"].isin(["Orange", "Rouge"])].copy()

    view = view.sort_values("Date_Clean", ascending=False).head(limit)
    if view.empty:
        st.info("Aucune observation grave sur la période sélectionnée.")
        return

    color_styles = {
        "Vert": {"border": "#2ecc71", "bg": "#ecfdf5", "txt": "#166534", "bd": "#86efac"},
        "Jaune": {"border": "#f1c40f", "bg": "#fefce8", "txt": "#854d0e", "bd": "#fde68a"},
        "Orange": {"border": "#e67e22", "bg": "#fff7ed", "txt": "#9a3412", "bd": "#fdba74"},
        "Rouge": {"border": "#e74c3c", "bg": "#fef2f2", "txt": "#991b1b", "bd": "#fca5a5"},
    }

    for _, row in view.iterrows():
        color = row.get("Couleur_Clean", "-")
        palette = color_styles.get(color, {"border": "#94a3b8", "bg": "#f8fafc", "txt": "#334155", "bd": "#cbd5e1"})

        date_txt = row["Date_Clean"].strftime("%d/%m/%Y %H:%M") if pd.notna(row.get("Date_Clean")) else "Date inconnue"
        eleve = row.get(cols["eleve"], "-") if cols.get("eleve") in row else "-"
        classe = row.get(cols["classe"], "-") if cols.get("classe") in row else "-"

        adult = ""
        if cols.get("adult") and cols["adult"] in view.columns and pd.notna(row.get(cols["adult"])):
            adult = f" · {row.get(cols['adult'])}"

        obs_text = ""
        if cols.get("obs") and cols["obs"] in view.columns and pd.notna(row.get(cols["obs"])):
            obs_text = truncate_text(row.get(cols["obs"]))

        severe_cls = " severe" if color in ["Orange", "Rouge"] else ""
        st.markdown(
            f"""
            <div class='obs-card{severe_cls}' style='border-left-color:{palette['border']};'>
                <div class='obs-meta'>
                    {date_txt}
                    <span class='obs-badge' style='background:{palette['bg']}; color:{palette['txt']}; border-color:{palette['bd']};'>{color}</span>
                </div>
                <div class='obs-main'><b>{eleve}</b> · {classe}{adult}</div>
                {f"<div class='obs-note'>{obs_text}</div>" if obs_text else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )


def ensure_color_columns(pivot_df):
    for color in COLOR_ORDER:
        if color not in pivot_df.columns:
            pivot_df[color] = 0
    return pivot_df


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
        c_main, c_pie = st.columns([2, 1])
        with c_main:
            st.subheader("Analyse Temporelle")
            df_inc = df_f[df_f["Couleur_Clean"] != "Vert"]
            if not df_inc.empty:
                heat = df_inc.groupby(["Jour_Fr", "Heure"]).size().reset_index(name="Count")
                fig = px.density_heatmap(
                    heat,
                    x="Heure",
                    y="Jour_Fr",
                    z="Count",
                    color_continuous_scale="Reds",
                    category_orders={"Jour_Fr": DAYS_ORDER},
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("Calme plat.")
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

        st.divider()
        obs_col, sev_col = st.columns(2)
        with obs_col:
            render_observation_cards(df_f, cols, "5 dernières observations", severe_only=False, limit=5)
        with sev_col:
            render_observation_cards(df_f, cols, "3 dernières observations graves", severe_only=True, limit=3)

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

        de_full = df[df[col_eleve] == sel_eleve].copy().sort_values("Date_Clean", ascending=True)

        c_evol, c_hist = st.columns([1, 2])
        with c_evol:
            if not de_full.empty:
                st.metric("Total Entrées", len(de_full))
                dom_mois = de_full.groupby("Mois_Str")["Couleur_Clean"].agg(lambda x: x.mode().iloc[0])
                st.write("**Dominante par Mois:**")
                st.dataframe(dom_mois, use_container_width=True)
        with c_hist:
            if not de_full.empty:
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
                cols_show = [col_date, "Heure", "Couleur_Clean", col_adult, col_obs]
                cols_final = [c for c in cols_show if c in de_full.columns and c is not None]
                st.dataframe(
                    de_full.sort_values("Date_Clean", ascending=False)[cols_final],
                    use_container_width=True,
                )

    with t7:
        if col_adult in df.columns:
            c1, c2 = st.columns([1, 3])
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

    except Exception:
        st.title("🎓 Pilotage Vie Scolaire")
        st.error(
            "Impossible de charger les données Google Sheets. Vérifiez le nom de l'onglet, "
            "les permissions du document et les secrets Streamlit."
        )


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

    except Exception:
        st.title("🎓 Pilotage Vie Scolaire")
        st.error(
            "Impossible de charger les données Google Sheets. Vérifiez le nom de l'onglet, "
            "les permissions du document et les secrets Streamlit."
        )
