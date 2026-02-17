import streamlit as st
import os
import subprocess
import pandas as pd
import base64
import json
import tkinter as tk
from tkinter import filedialog

# --- CONFIGURATION ---
st.set_page_config(page_title="NSI Explorer Turbo", layout="wide")

# Optimisation CSS
st.markdown("""
    <style>
    div.row-widget.stRadio > div{flex-direction:column;}
    .stRadio [data-testid="stWidgetLabel"] p {font-size: 18px; font-weight: bold;}
    /* Fixe la hauteur de la zone de liste pour éviter de tout recalculer */
    .stColumn:first-child { max-height: 90vh; overflow-y: auto; }
    </style>
    """, unsafe_allow_html=True)

# --- FONCTIONS CACHÉES (POUR LA VITESSE) ---

@st.cache_data(show_spinner="Scan des fichiers en cours...")
def get_files_list(base_path):
    """Scanne le dossier une seule fois et garde le résultat en mémoire."""
    extensions = {'.tex', '.md', '.ipynb', '.csv', '.py', '.pdf'}
    files_data = []
    for root, _, files in os.walk(base_path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in extensions:
                full_path = os.path.join(root, f)
                files_data.append({
                    "Fichier": f,
                    "Type": ext,
                    "Complet": full_path
                })
    return pd.DataFrame(files_data)

@st.cache_data
def convert_df(df):
    # On convertit le dataframe en CSV (encodage utf-8 pour les accents)
    return df.to_csv(index=False).encode('utf-8')

@st.cache_resource
def get_pdf_display(file_path):
    """Mise en cache de l'encodage PDF pour un affichage instantané."""
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    return f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">'

def select_folder_linux():
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askdirectory(master=root)
        root.destroy()
        return path
    except:
        return None

# --- LOGIQUE APP ---
st.title("📂 NSI Explorer Turbo 🚀")

if 'base_path' not in st.session_state:
    st.session_state.base_path = os.getcwd()

# Barre latérale
with st.sidebar:
    st.header("⚙️ Paramètres")
    
    if st.button("📁 Sélectionner un dossier"):
        path = select_folder_linux()
        if path: 
            st.session_state.base_path = path
            st.cache_data.clear() # On vide le cache si on change de dossier
            st.rerun()
    st.info(f"Dossier : \n`{st.session_state.base_path}`")
    if st.button("🔄 Rafraîchir la liste"):
        st.cache_data.clear()
        st.rerun()
    
# 1. RÉCUPÉRATION DES DONNÉES (VIA CACHE)
df = get_files_list(st.session_state.base_path)
if not df.empty:
        st.write("---")
        st.subheader("💾 Export")
        csv_data = convert_df(df)
        st.download_button(
            label="📥 Télécharger la liste (CSV)",
            data=csv_data,
            file_name='liste_fichiers_nsi.csv',
            mime='text/csv',
        )
if not df.empty:
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("📋 Documents")
        search = st.text_input("🔍 Filtrer...", placeholder="Nom du fichier...")
        
        filtered_df = df
        if search:
            filtered_df = df[df['Fichier'].str.contains(search, case=False)]

        if not filtered_df.empty:
            # On utilise un index pour éviter les erreurs de sélection
            selected_file_name = st.radio(
                "Sélection :",
                options=filtered_df['Fichier'].tolist(),
                label_visibility="collapsed",
                key="file_selector"
            )
            selected_row = filtered_df[filtered_df['Fichier'] == selected_file_name].iloc[0]
            f_path = selected_row['Complet']
            f_ext = selected_row['Type']
        else:
            selected_file_name = None

    with col_right:
        if selected_file_name:
            head_col, btn_col = st.columns([2, 1])
            head_col.subheader(f"👁️ {selected_file_name}")
            if btn_col.button("🖥️ Ouvrir (Système)", width='stretch'):
                subprocess.Popen(['xdg-open', f_path])

            with st.container(border=True):
                if f_ext == '.pdf':
                    st.markdown(get_pdf_display(f_path), unsafe_allow_html=True)
                
                elif f_ext == '.ipynb':
                    try:
                        with open(f_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        for cell in content.get('cells', []):
                            if cell['cell_type'] == 'code':
                                st.code("".join(cell['source']), language='python')
                            elif cell['cell_type'] == 'markdown':
                                st.markdown("".join(cell['source']))
                    except: st.error("Erreur de lecture Notebook.")
                
                elif f_ext in ['.py', '.md', '.tex']:
                    with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lang = 'python' if f_ext == '.py' else 'markdown'
                        st.code(f.read(), language=lang)
                
                elif f_ext == '.csv':
                    st.dataframe(pd.read_csv(f_path), width='stretch')
else:
    st.warning("Aucun fichier trouvé.")