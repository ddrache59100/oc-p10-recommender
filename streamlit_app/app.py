"""
My Content Recommender - Interface Streamlit
Application de démonstration du système de recommandation
"""

import streamlit as st
import pandas as pd
import requests
import json
from pathlib import Path
import time
from typing import Dict, List, Tuple

# Configuration de la page
st.set_page_config(
    page_title="My Content Recommender",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration des chemins
DATA_DIR = Path(__file__).parent / "data"
SAMPLE_FILE = DATA_DIR / "clicks_sample.csv"
FULL_FILE = DATA_DIR / "clicks.parquet"

# URL de l'API Azure Functions
import os
API_URL = os.getenv('AZURE_FUNCTION_URL', 'http://localhost:7071') + "/api/recommend"

# Seuils pour les profils utilisateurs
COLD_START_THRESHOLD = 5
ACTIVE_THRESHOLD = 15

# --- Fonctions de chargement des données ---

@st.cache_data
def load_click_data(use_sample: bool = True) -> Tuple[pd.DataFrame, str]:
    """Charge les données de clics."""
    if use_sample:
        if SAMPLE_FILE.exists():
            df = pd.read_csv(SAMPLE_FILE)
            return df, "sample"
        else:
            st.error(f"❌ Fichier non trouvé : {SAMPLE_FILE}")
            return pd.DataFrame(), "error"
    else:
        if FULL_FILE.exists():
            with st.spinner("Chargement du dataset complet (52 MB)..."):
                df = pd.read_parquet(FULL_FILE)
            return df, "full"
        else:
            st.error(f"❌ Fichier non trouvé : {FULL_FILE}")
            return pd.DataFrame(), "error"

@st.cache_data
def create_user_histories(df: pd.DataFrame) -> Tuple[Dict, Dict]:
    """Crée les dictionnaires d'historiques et statistiques utilisateurs."""
    histories = {}
    user_stats = {}
    
    grouped = df.groupby('user_id')
    for user_id, group in grouped:
        articles = group['click_article_id'].tolist()
        histories[str(user_id)] = articles
        user_stats[str(user_id)] = {
            'n_clicks': len(articles),
            'n_unique': len(set(articles))
        }
    
    return histories, user_stats

@st.cache_data
def get_article_popularity(df: pd.DataFrame, top_n: int = 100) -> List[int]:
    """Récupère les articles les plus populaires."""
    article_counts = df['click_article_id'].value_counts()
    return article_counts.head(top_n).index.tolist()

# --- Fonctions utilitaires ---

def get_user_profile(n_articles: int) -> Tuple[str, str]:
    """Détermine le profil utilisateur basé sur le nombre d'articles."""
    if n_articles < COLD_START_THRESHOLD:
        return "Cold Start", "🆕"
    elif n_articles < ACTIVE_THRESHOLD:
        return "Moderate", "📊"
    else:
        return "Active", "🔥"

def check_api_connection() -> bool:
    """Vérifie la connexion à l'API."""
    try:
        response = requests.post(
            f"{API_URL}/1",
            json={"history": [], "n_recommendations": 1},
            timeout=2
        )
        return response.status_code == 200
    except:
        return False

def call_recommendation_api(user_id: int, history: List[int], n_recommendations: int = 5) -> Dict:
    """Appelle l'API Azure Functions pour obtenir des recommandations."""
    try:
        url = f"{API_URL}/{user_id}"
        payload = {
            "history": history,
            "n_recommendations": n_recommendations
        }
        
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "error": f"API returned status {response.status_code}",
                "recommendations": []
            }
            
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "error": "API non connectée",
            "recommendations": []
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "recommendations": []
        }

# --- Interface principale ---

def main():
    # Titre
    st.title("🎯 My Content Recommender")
    
    # Initialisation session state
    if 'api_connected' not in st.session_state:
        st.session_state.api_connected = check_api_connection()
    
    # ========== SIDEBAR ==========
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Status API avec indicateur visuel
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.api_connected:
                st.success("✅ API connectée")
            else:
                st.error("❌ API déconnectée")
        with col2:
            if st.button("🔄"):
                st.session_state.api_connected = check_api_connection()
                st.rerun()
        
        st.divider()
        
        # Source de données
        data_mode = st.radio(
            "📊 Source de données",
            ["Échantillon (rapide)", "Dataset complet (52 MB)"],
            index=0
        )
        use_sample = "Échantillon" in data_mode
        
        # Nombre de recommandations
        n_recommendations = st.slider(
            "Nombre de recommandations",
            min_value=3,
            max_value=10,
            value=5
        )
        
        st.divider()
        
        # Mode utilisateur
        user_mode = st.radio(
            "👤 Mode",
            ["Rechercher un utilisateur", "Nouvel utilisateur"]
        )
        
        # Mode de sélection pour recherche
        if user_mode == "Rechercher un utilisateur":
            search_mode = st.radio(
                "🔍 Méthode",
                ["Par ID", "Menu déroulant"]
            )
        
        st.divider()
        
        # Légende des profils
        st.caption("**Profils utilisateurs:**")
        st.caption("🆕 Cold Start: < 5 articles")
        st.caption("📊 Moderate: 5-14 articles")
        st.caption("🔥 Active: ≥ 15 articles")
    
    # Chargement des données
    df, status = load_click_data(use_sample)
    if df.empty:
        st.error("Impossible de charger les données")
        return
    
    histories, user_stats = create_user_histories(df)
    popular_articles = get_article_popularity(df)
    
    # Métriques
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Utilisateurs", f"{len(histories):,}")
    with col2:
        st.metric("📰 Articles", f"{df['click_article_id'].nunique():,}")
    with col3:
        st.metric("🖱️ Interactions", f"{len(df):,}")
    with col4:
        st.metric("💾 Mode", "Sample" if use_sample else "Complet")
    
    st.divider()
    
    # ========== COLONNES PRINCIPALES ==========
    col_user, col_results = st.columns([1, 1])
    
    # ========== COLONNE GAUCHE: User + Historique ==========
    with col_user:
        st.subheader("👤 Utilisateur et Historique")
        
        if user_mode == "Rechercher un utilisateur":
            
            # Sélection par ID ou menu déroulant
            if search_mode == "Par ID":
                user_id_input = st.number_input(
                    "ID utilisateur",
                    min_value=1,
                    max_value=999999,
                    value=1,
                    step=1,
                    key="search_user_id"
                )
                user_id_str = str(user_id_input)
            else:  # Menu déroulant
                # Trier les utilisateurs par activité
                sorted_users = sorted(
                    histories.keys(),
                    key=lambda x: user_stats[x]['n_clicks'],
                    reverse=True
                )[:100]  # Top 100
                
                # Créer les labels avec profils
                user_options = []
                user_labels = []
                for uid in sorted_users:
                    n_clicks = user_stats[uid]['n_clicks']
                    profile, icon = get_user_profile(n_clicks)
                    user_options.append(uid)
                    user_labels.append(f"{icon} User {uid} ({n_clicks} clics - {profile})")
                
                selected_idx = st.selectbox(
                    "Sélectionner un utilisateur",
                    range(len(user_options)),
                    format_func=lambda x: user_labels[x]
                )
                user_id_str = user_options[selected_idx]
                user_id_input = int(user_id_str)
            
            # Traitement de l'utilisateur sélectionné
            if user_id_str in histories:
                history = histories[user_id_str]
                n_clicks = user_stats[user_id_str]['n_clicks']
                profile_name, profile_icon = get_user_profile(n_clicks)
                
                # Affichage du profil
                st.info(f"{profile_icon} **Profil: {profile_name}**")
                
                # Statistiques
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Clics totaux", n_clicks)
                with col_b:
                    st.metric("Articles uniques", user_stats[user_id_str]['n_unique'])
                
                # Historique
                with st.expander("📚 Voir l'historique", expanded=True):
                    if len(history) > 20:
                        st.write(f"**Premiers articles:** {history[:10]}")
                        st.write(f"**Derniers articles:** {history[-10:]}")
                        st.write(f"**Total:** {len(history)} articles")
                    else:
                        st.write(f"**Articles consultés:** {history}")
                
            else:
                st.warning(f"⚠️ Utilisateur {user_id_input} non trouvé")
                
                if st.checkbox("Créer comme nouvel utilisateur"):
                    history = []
                    st.info("💡 Utilisateur créé en mode Cold Start")
                else:
                    history = None
            
            # Bouton de recommandation
            if history is not None:
                if st.button("🚀 Générer des recommandations", type="primary", use_container_width=True):
                    with col_results:
                        generate_recommendations(user_id_input, history, n_recommendations)
        
        else:  # Nouvel utilisateur
            st.info("Créer un nouvel utilisateur")
            
            new_user_id = st.number_input(
                "ID du nouvel utilisateur",
                min_value=400000,
                value=400001,
                step=1,
                key="new_user"
            )
            
            # Option pour l'historique
            with_history = st.checkbox("Ajouter un historique initial")
            
            if with_history:
                selected_articles = st.multiselect(
                    "Sélectionner des articles consultés",
                    options=popular_articles[:50],
                    format_func=lambda x: f"Article {x}",
                    max_selections=20
                )
                history = selected_articles
                
                if history:
                    profile_name, profile_icon = get_user_profile(len(history))
                    st.success(f"✅ {len(history)} articles → {profile_icon} {profile_name}")
            else:
                history = []
                st.info("🆕 Mode Cold Start (recommandations populaires)")
            
            # Bouton de recommandation
            if st.button("🚀 Générer des recommandations", type="primary", use_container_width=True):
                with col_results:
                    generate_recommendations(new_user_id, history, n_recommendations)
    
    # ========== COLONNE DROITE: Résultats ==========
    with col_results:
        if 'last_result' not in st.session_state:
            st.subheader("📊 Résultats")
            st.info("👈 Sélectionnez un utilisateur et cliquez sur 'Générer des recommandations'")

def generate_recommendations(user_id: int, history: List[int], n_recommendations: int):
    """Génère et affiche les recommandations."""
    st.subheader("📊 Résultats")
    
    # Déterminer le profil attendu
    expected_profile, profile_icon = get_user_profile(len(history))
    
    with st.spinner("Appel de l'API..."):
        start_time = time.time()
        result = call_recommendation_api(
            int(user_id),
            history,
            n_recommendations
        )
        elapsed_time = (time.time() - start_time) * 1000
    
    st.session_state['last_result'] = result
    
    if result.get("status") == "error":
        st.error(f"❌ Erreur : {result.get('error')}")
        return
    
    # Métriques
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("⏱️ Temps total", f"{elapsed_time:.1f} ms")
    with col2:
        st.metric("🔄 Temps API", f"{result.get('inference_time_ms', 0):.1f} ms")
    with col3:
        st.metric("📊 Profil", f"{profile_icon} {expected_profile}")
    
    st.divider()
    
    # Recommandations
    recommendations = result.get('recommendations', [])
    if not recommendations:
        st.warning("Aucune recommandation générée")
        return
    
    st.subheader("📰 Articles recommandés")
    
    for i, rec in enumerate(recommendations, 1):
        with st.container():
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**#{i} - Article {rec['article_id']}**")
                score = rec.get('score', 0)
                st.progress(score, text=f"Score: {score:.3f}")
            
            with col2:
                method = rec.get('method', 'unknown')
                if 'content_based' in method:
                    st.success("🔍 Similarité")
                elif method == 'popular':
                    st.warning("⭐ Populaire")
                else:
                    st.info(f"📊 {method}")
    
    with st.expander("🔧 Détails JSON"):
        st.json(result)

if __name__ == "__main__":
    main()