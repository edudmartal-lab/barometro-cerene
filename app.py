import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="CERENE | Manager V42",
    layout="wide",
    page_icon="🛡️",
    initial_sidebar_state="expanded"
)

# --- CSS LIMPIO ---
st.markdown("""
    <style>
    .stApp { background-color: #f4f6f9; }
    h1, h2, h3 { color: #1e293b; font-family: 'Segoe UI', sans-serif; }
    
    /* Métricas */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    
    /* Pestañas */
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
    
    /* Tablas */
    div[data-testid="stDataFrame"] { width: 100%; }
    
    /* Cita Mistral */
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
    
    /* Alertas visuales */
    .alert-ln { background-color: #fefce8; border: 1px solid #eab308; color: #854d0e; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    .alert-diego { background-color: #fef2f2; border: 1px solid #ef4444; color: #991b1b; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. USUARIOS ---
USERS = st.secrets["users"]
# --- 3. LOGIN ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    if not st.session_state.password_correct:
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            st.write("")
            with st.container(border=True):
                img_path = "VS Noel.jpeg"
                if os.path.exists(img_path): st.image(img_path, use_container_width=True)
                st.subheader("🔐 Connexion")
                user = st.text_input("Identifiant", key="u_in")
                pwd = st.text_input("Mot de passe", type="password", key="p_in")
                if st.button("Se connecter", type="primary", use_container_width=True):
                    if user.lower() in USERS and USERS[user.lower()] == pwd:
                        st.session_state.password_correct = True
                        st.session_state.real_user = user
                        st.rerun()
                    else: st.error("Erreur d'identifiants.")
        return False
    return True

if check_password():
    # --- SIDEBAR ---
    with st.sidebar:
        img_path = "VS Noel.jpeg"
        if os.path.exists(img_path): st.image(img_path, use_container_width=True)
        st.write("")
        u = st.session_state.get("real_user", "User")
        st.caption(f"Connecté: **{u.capitalize()}**")
        
        st.markdown("""
        <div class='mistral-box'>
        "Beaucoup de choses peuvent attendre, mais pas l'enfant... Son nom est Aujourd'hui."
        <br><b>- Gabriela Mistral</b>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        uploaded_file = st.file_uploader("📂 Charger Données", type=["xlsx", "csv"])
        if st.button("Déconnexion"):
            st.session_state.password_correct = False
            st.rerun()

    if uploaded_file is None:
        st.title("🎓 Pilotage Vie Scolaire")
        st.info("👋 Veuillez charger le fichier Excel/CSV dans la barre latérale.")
        st.stop()

    # --- PROCESAMIENTO ROBUSTO ---
    try:
        # 1. Carga
        if uploaded_file.name.endswith('.csv'): 
            try:
                df = pd.read_csv(uploaded_file)
                if len(df.columns) < 2: 
                    uploaded_file.seek(0)
                    df = pd.read_csv(uploaded_file, sep=';')
            except:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1')
        else: 
            df = pd.read_excel(uploaded_file)

        # 2. Limpieza Nombres
        df.columns = [str(c).strip() for c in df.columns]
        
        # 3. Detectar Columnas
        col_color = next((c for c in df.columns if 'Couleur' in c or 'Color' in c), None)
        col_eleve = next((c for c in df.columns if 'Élève' in c or 'Eleve' in c or 'Nom' in c), None)
        col_classe = next((c for c in df.columns if 'Classe' in c or 'Clase' in c), None)
        col_obs = next((c for c in df.columns if 'Observation' in c or 'Observacion' in c), None)
        col_adult = next((c for c in df.columns if 'Adulte' in c or 'Prof' in c or 'Adult' in c), "Adulte")
        col_date = next((c for c in df.columns if 'Horodateur' in c or 'Timestamp' in c or 'Date' in c or c == 'c'), None)
        
        if not col_date and len(df.columns) > 0: 
            col_date = df.columns[0]
            
        if not (col_color and col_eleve and col_classe and col_date):
            st.error(f"Colonnes manquantes. Trouvé: {list(df.columns)}")
            st.stop()

        # 4. Limpieza Datos Nulos
        df = df.dropna(subset=[col_eleve, col_date, col_color])

        # 5. Mapeos
        color_map = {'Vert': 'Vert', 'Verde': 'Vert', 'Jaune': 'Jaune', 'Amarillo': 'Jaune', 'Orange': 'Orange', 'Naranja': 'Orange', 'Rouge': 'Rouge', 'Rojo': 'Rouge'}
        days_map = {'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi', 'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'}
        
        df['Couleur_Clean'] = df[col_color].map(color_map).fillna(df[col_color])
        
        # 6. FECHA (CRÍTICO: HACERLO AQUÍ PARA SIEMPRE)
        df['Date_Clean'] = pd.to_datetime(df[col_date], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date_Clean'])
        
        # 7. Derivados de Fecha
        df['Semaine'] = df['Date_Clean'].dt.isocalendar().week
        df['Mois_Str'] = df['Date_Clean'].dt.strftime('%Y-%m')
        df['Semaine_Str'] = df['Date_Clean'].dt.strftime('%Y-W%V')
        
        def get_p(d):
            if pd.isna(d): return "Hors"
            if (9<=d.month) or (d.month==10 and d.day<=18): return "P1"
            if (d.month==10 and d.day>18) or (d.month>=11): return "P2"
            return "P3+"
        
        df['Période'] = df['Date_Clean'].apply(get_p)
        df['Jour_Fr'] = df['Date_Clean'].dt.day_name().map(days_map)
        df['Heure'] = df['Date_Clean'].dt.hour

        with st.sidebar:
            st.write("🔎 **Filtres Actifs**")
            all_p = sorted(df['Période'].unique().astype(str))
            if all_p:
                sel_p = st.selectbox("Période", all_p, index=len(all_p)-1)
                df_p = df[df['Période'] == sel_p].copy()
            else:
                df_p = df.copy()

            all_w = sorted(df_p['Semaine'].unique())
            sel_w = st.multiselect("Semaines", all_w, default=all_w)
            if sel_w: df_f = df_p[df_p['Semaine'].isin(sel_w)].copy()
            else: df_f = df_p.copy()

        # --- TABS ---
        st.title("🎓 Pilotage Vie Scolaire")
        t1, t2, t3, t4, t5, t6, t7 = st.tabs(["📊 Vue Globale", "🏫 Classes", "📋 Suivi", "⚖️ SANCTIONS", "🏆 HONNEUR", "👤 Dossier", "👥 Équipe"])

        # T1 GLOBAL
        with t1:
            k1, k2, k3, k4 = st.columns(4)
            tot = len(df_f)
            v = len(df_f[df_f['Couleur_Clean']=='Vert'])
            j = len(df_f[df_f['Couleur_Clean']=='Jaune'])
            inc = len(df_f[df_f['Couleur_Clean'].isin(['Rouge','Orange'])])
            k1.metric("Total", tot)
            k2.metric("Verts", v, delta="Positif")
            k3.metric("Jaunes", j, delta_color="off")
            k4.metric("Incidents", inc, delta="-Alertes", delta_color="inverse")
            st.divider()
            c_main, c_pie = st.columns([2, 1])
            with c_main:
                st.subheader("Analyse Temporelle")
                df_inc = df_f[df_f['Couleur_Clean']!='Vert']
                if not df_inc.empty:
                    heat = df_inc.groupby(['Jour_Fr', 'Heure']).size().reset_index(name='Count')
                    fig = px.density_heatmap(heat, x='Heure', y='Jour_Fr', z='Count', color_continuous_scale='Reds', category_orders={"Jour_Fr":['Lundi','Mardi','Mercredi','Jeudi','Vendredi']})
                    st.plotly_chart(fig, use_container_width=True)
                else: st.success("Calme plat.")
            with c_pie:
                st.subheader("Répartition")
                cts = df_f['Couleur_Clean'].value_counts()
                figp = px.pie(values=cts, names=cts.index, color=cts.index, color_discrete_map={'Vert':'#2ecc71', 'Jaune':'#f1c40f', 'Orange':'#e67e22', 'Rouge':'#e74c3c'})
                st.plotly_chart(figp, use_container_width=True)

        # T2 CLASSES
        with t2:
            st.subheader("Analyse par Classe")
            df_class = df_f.groupby([col_classe, 'Couleur_Clean']).size().unstack(fill_value=0)
            
            # --- FIX SYNTAXIS: BUCLES EXPANDIDOS ---
            for c in ['Vert', 'Jaune', 'Orange', 'Rouge']:
                if c not in df_class.columns:
                    df_class[c] = 0
            
            piv = df_f.groupby([col_eleve, col_classe])['Couleur_Clean'].value_counts().unstack(fill_value=0)
            
            # --- FIX SYNTAXIS: BUCLES EXPANDIDOS ---
            for c in ['Vert','Jaune','Orange','Rouge']:
                if c not in piv.columns:
                    piv[c] = 0
            
            # Cálculo de riesgos
            piv['Is_Incident'] = (piv['Orange'] >= 1) | (piv['Rouge'] >= 1)
            risk = piv.reset_index().groupby(col_classe)['Is_Incident'].sum()
            full_stats = df_class.join(risk).fillna(0)
            
            st.bar_chart(full_stats[['Vert','Jaune','Orange','Rouge']], color=['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c'])
            
            if not full_stats.empty:
                st.divider()
                st.subheader("🏆 Podiums")
                c_best = full_stats['Vert'].idxmax()
                c_inc = (full_stats['Orange'] + full_stats['Rouge']).idxmax()
                
                # HTML activado correctamente
                st.markdown(f"""
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
                """, unsafe_allow_html=True)
            
            st.write("#### Détails")
            st.dataframe(full_stats[['Vert','Jaune','Orange','Rouge']], use_container_width=True)

        # T3 SUIVI
        with t3:
            st.subheader("📋 Listes de Suivi Éducatif")
            
            piv = df_f.groupby([col_eleve, col_classe])['Couleur_Clean'].value_counts().unstack(fill_value=0)
            # --- FIX SYNTAXIS: BUCLES EXPANDIDOS ---
            for c in ['Vert','Jaune','Orange','Rouge']:
                if c not in piv.columns:
                    piv[c] = 0
            
            c_ln, c_d = st.columns(2)
            
            # Lógica Linda/Nelson
            cond_accum = (piv['Jaune'] >= 3) & (piv['Orange'] == 0) & (piv['Rouge'] == 0)
            cond_aisle = (piv['Orange'] == 1) & (piv['Jaune'] == 0) & (piv['Rouge'] == 0)
            filter_ln = cond_accum | cond_aisle
            
            # Lógica Diego
            cond_red = (piv['Rouge'] >= 1)
            cond_org_yel = (piv['Orange'] >= 1) & (piv['Jaune'] >= 1)
            cond_multi_org = (piv['Orange'] >= 2)
            filter_d = cond_red | cond_org_yel | cond_multi_org
            
            with c_ln:
                st.markdown('<div class="alert-ln"><b>👩‍🏫 Suivi LINDA & NELSON</b><br>• Accumulation Jaunes (≥3)<br>• 1 Orange "isolée" (sans jaunes)</div>', unsafe_allow_html=True)
                st.dataframe(piv[filter_ln][['Orange', 'Jaune']], use_container_width=True)

            with c_d:
                st.markdown('<div class="alert-diego"><b>👨‍🏫 Suivi DIEGO</b><br>• Incidents (Rouge)<br>• Orange + Jaune<br>• Récidive Orange (≥2)</div>', unsafe_allow_html=True)
                st.dataframe(piv[filter_d][['Rouge','Orange','Jaune']], use_container_width=True)

        # T4 SANCTIONS
        with t4:
            st.markdown('<h3 style="color:#b91c1c;">⚖️ SANCTIONS & RETENUES</h3>', unsafe_allow_html=True)
            piv_sanc = df_f.groupby([col_eleve, col_classe])['Couleur_Clean'].value_counts().unstack(fill_value=0)
            # --- FIX SYNTAXIS: BUCLES EXPANDIDOS ---
            for c in ['Vert','Jaune','Orange','Rouge']:
                if c not in piv_sanc.columns:
                    piv_sanc[c] = 0
            
            piv_sanc['Oranges_Virtuelles'] = piv_sanc['Orange'] + (piv_sanc['Jaune'] // 3)
            filter_r = (piv_sanc['Oranges_Virtuelles'] >= 2)
            df_r = piv_sanc[filter_r][['Oranges_Virtuelles', 'Rouge', 'Orange', 'Jaune']].sort_values('Oranges_Virtuelles', ascending=False)
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.info("ℹ️ **Règle :** 2 Oranges (ou équivalent) = 1 Retenue.")
                if not df_r.empty: st.metric("Élèves en Retenue", len(df_r), delta="Action requise", delta_color="inverse")
                else: st.metric("Retenues", 0)
            with c2:
                if not df_r.empty: st.dataframe(df_r, use_container_width=True)
                else: st.success("Aucune retenue.")

        # T5 HONNEUR (RESTAURADO)
        with t5:
            st.subheader("🏆 Tableau d'Honneur")
            st.markdown("""
            **Critères d'Excellence :**
            * 👍 **+1** par Vert
            * ⚠️ **-1** par Jaune
            * 🚨 **-2** par Orange
            * ⛔ **Disqualifié** si Rouge > 0 ou moins de 2 Verts.
            """)
            
            piv_hon = df_f.groupby([col_eleve, col_classe])['Couleur_Clean'].value_counts().unstack(fill_value=0)
            for c in ['Vert','Jaune','Orange','Rouge']:
                if c not in piv_hon.columns: piv_hon[c] = 0
                
            honors = []
            for idx, row in piv_hon.iterrows():
                if row['Rouge'] > 0 or row['Vert'] < 2:
                    score = -999
                else:
                    score = (row['Vert'] * 1) + (row['Jaune'] * -1) + (row['Orange'] * -2)
                
                honors.append({"Élève": idx[0], "Classe": idx[1], "Score": score, "Verts": row['Vert']})
            
            df_hon = pd.DataFrame(honors)
            if not df_hon.empty:
                df_winners = df_hon[df_hon['Score'] > 0].sort_values(['Score', 'Verts'], ascending=False)
                st.write("#### 🥇 Premiers de Classe")
                top_per_class = df_winners.loc[df_winners.groupby("Classe")["Score"].idxmax()]
                st.dataframe(top_per_class.set_index("Classe"), use_container_width=True)
                st.write("#### 📜 Liste Complète")
                st.dataframe(df_winners, use_container_width=True)
            else:
                st.info("Pas encore de données suffisantes.")

        # T6 DOSSIER (FIX DATE_CLEAN & SORT)
        with t6:
            st.subheader("👤 Dossier & Évolution")
            eleves = sorted(df[col_eleve].astype(str).unique())
            sel_eleve = st.selectbox("Rechercher un élève", eleves)
            
            # FIX: Copia explicita y ordenamiento PREVIO
            de_full = df[df[col_eleve]==sel_eleve].copy()
            de_full = de_full.sort_values('Date_Clean', ascending=True)
            
            c_evol, c_hist = st.columns([1, 2])
            with c_evol:
                if not de_full.empty:
                    st.metric("Total Entrées", len(de_full))
                    try:
                        dom_mois = de_full.groupby('Mois_Str')['Couleur_Clean'].agg(lambda x: x.mode().iloc[0])
                        st.write("**Dominante par Mois:**")
                        st.dataframe(dom_mois, use_container_width=True)
                    except: st.write("Données insuffisantes.")
            with c_hist:
                if not de_full.empty:
                    evol = de_full.groupby(['Semaine_Str', 'Couleur_Clean']).size().reset_index(name='Count')
                    fig = px.bar(evol, x='Semaine_Str', y='Count', color='Couleur_Clean', title="Évolution Hebdomadaire", color_discrete_map={'Vert':'#2ecc71', 'Jaune':'#f1c40f', 'Orange':'#e67e22', 'Rouge':'#e74c3c'})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.write("**Historique**")
                    cols_show = [col_date, 'Heure', 'Couleur_Clean', col_adult, col_obs]
                    # FIX: Seleccionar columnas DESPUES de haber ordenado y limpiado
                    cols_final = [c for c in cols_show if c in de_full.columns]
                    # Invertir para mostrar lo más reciente arriba
                    st.dataframe(de_full.sort_values('Date_Clean', ascending=False)[cols_final], use_container_width=True)

        # T7 EQUIPE
        with t7:
            if col_adult in df.columns:
                c1, c2 = st.columns([1, 3])
                with c1: sel_p = st.selectbox("Professeur", ["Global"] + sorted(df_f[col_adult].astype(str).unique()))
                with c2:
                    if sel_p == "Global":
                        fig = px.histogram(df_f, x=col_adult, color='Couleur_Clean', barmode='stack', color_discrete_map={'Vert':'#2ecc71', 'Jaune':'#f1c40f', 'Orange':'#e67e22', 'Rouge':'#e74c3c'})
                    else:
                        sub = df_f[df_f[col_adult]==sel_p]
                        fig = px.histogram(sub, x='Jour_Fr', color='Couleur_Clean', category_orders={"Jour_Fr":['Lundi','Mardi','Mercredi','Jeudi','Vendredi']}, color_discrete_map={'Vert':'#2ecc71', 'Jaune':'#f1c40f', 'Orange':'#e67e22', 'Rouge':'#e74c3c'})
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur technique : {e}")