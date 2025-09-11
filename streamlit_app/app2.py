"""
My Content Recommender - Interface Streamlit
Application de démonstration du système de recommandation
Version optimisée basée sur le code GitHub original
"""

import streamlit as st
import pandas as pd
import requests
import json
from pathlib import Path
import time
from typing import Dict, List, Tuple
import random

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

# Limite pour le menu déroulant (dataset complet uniquement)
MAX_DROPDOWN_USERS = 100

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
                # Pour le dataset complet, charger seulement un échantillon pour le menu
                df = pd.read_parquet(FULL_FILE)
            return df, "full"
        else:
            st.error(f"❌ Fichier non trouvé : {FULL_FILE}")
            return pd.DataFrame(), "error"

@st.cache_data
def create_user_histories(df: pd.DataFrame, limit_for_dropdown: bool = False) -> Tuple[Dict, Dict]:
    """
    Crée les dictionnaires d'historiques et statistiques utilisateurs.
    
    Args:
        df: DataFrame des clics
        limit_for_dropdown: Si True, limite aux top users pour le dataset complet
    """
    histories = {}
    user_stats = {}
    
    # Pour le dataset complet, limiter si nécessaire
    if limit_for_dropdown and len(df) > 100000:
        # Prendre seulement les users les plus actifs
        top_users = df['user_id'].value_counts().head(MAX_DROPDOWN_USERS).index
        df_limited = df[df['user_id'].isin(top_users)]
        grouped = df_limited.groupby('user_id')
    else:
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
def load_user_history_by_id(user_id: int, use_sample: bool = True) -> Tuple[List[int], Dict]:
    """Charge l'historique d'un utilisateur spécifique (optimisé pour grands datasets)."""
    try:
        if use_sample and SAMPLE_FILE.exists():
            df = pd.read_csv(SAMPLE_FILE)
            user_data = df[df['user_id'] == user_id]
        elif not use_sample and FULL_FILE.exists():
            # Utiliser les filtres Parquet pour ne charger que les données nécessaires
            df = pd.read_parquet(
                FULL_FILE,
                filters=[('user_id', '==', user_id)]
            )
            user_data = df
        else:
            return [], {}
        
        if not user_data.empty:
            articles = user_data['click_article_id'].tolist()
            stats = {
                'n_clicks': len(articles),
                'n_unique': len(set(articles))
            }
            return articles, stats
        else:
            return [], {}
            
    except Exception as e:
        st.warning(f"Erreur chargement historique: {e}")
        return [], {}

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
            API_URL,
            json={"user_id": 1, "history": [], "n_recommendations": 1},
            timeout=2
        )
        return response.status_code == 200
    except:
        return False

def call_recommendation_api(user_id: int, history: List[int], n_recommendations: int = 5) -> Dict:
    """Appelle l'API Azure Functions pour obtenir des recommandations."""
    try:
        payload = {
            "user_id": user_id,
            "history": history,
            "n_recommendations": n_recommendations
        }
        
        response = requests.post(
            API_URL,
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

def generate_recommendations(user_id: int, history: List[int], n_recommendations: int):
    """Génère et affiche les recommandations."""
    st.subheader("📊 Résultats")
    
    # Timer et appel API
    start_time = time.time()
    with st.spinner("🔮 Génération des recommandations..."):
        result = call_recommendation_api(user_id, history, n_recommendations)
    total_time = (time.time() - start_time) * 1000
    
    # Affichage des résultats
    if result['status'] == 'success':
        st.success(f"✅ **{len(result['recommendations'])} recommandations générées**")
        
        # Métriques
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("⏱️ Temps API", f"{result.get('inference_time_ms', 0):.1f}ms")
        with col_b:
            st.metric("📡 Temps total", f"{total_time:.1f}ms")
        with col_c:
            cache_icon = "✅" if result.get('from_cache') else "❌"
            st.metric("💾 Cache", cache_icon)
        
        # Recommandations
        st.write("### 🎯 Articles recommandés")
        
        for rec in result['recommendations']:
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.write(f"**#{rec['rank']}**")
            with col2:
                st.write(f"Article **{rec['article_id']}**")
            with col3:
                st.write(f"Score: **{rec['score']:.3f}**")
        
        # Score moyen
        scores = [r['score'] for r in result['recommendations']]
        avg_score = sum(scores) / len(scores) if scores else 0
        st.info(f"📊 Score moyen de similarité: **{avg_score:.3f}**")
        
    elif result['status'] == 'cold_start':
        st.info("❄️ **Mode Cold Start**: Articles populaires recommandés")
        
        for rec in result['recommendations']:
            st.write(f"#{rec['rank']} - Article {rec['article_id']} (Score: {rec['score']:.3f})")
            
    else:  # error
        st.error(f"❌ **Erreur**: {result.get('error', 'Erreur inconnue')}")
        
        if result.get('recommendations'):
            st.warning("⚠️ Recommandations de fallback:")
            for rec in result['recommendations']:
                st.write(f"Article {rec['article_id']}")
    
    # Sauvegarder le résultat
    st.session_state['last_result'] = result

# --- Interface principale ---

def main():
    # Titre
    st.title("🎯 My Content Recommender")
    st.markdown("**Système de recommandation Content-Based** - Projet 10 OpenClassrooms")
    
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
            ["Rechercher un utilisateur", "Nouvel utilisateur", "Utilisateur aléatoire"]
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
    
    # Pour le dataset sample, charger tous les historiques
    # Pour le dataset complet, charger seulement pour le menu déroulant
    if use_sample:
        histories, user_stats = create_user_histories(df, limit_for_dropdown=False)
    else:
        # Pour le dataset complet, on charge à la demande
        histories = {}
        user_stats = {}
        if user_mode == "Rechercher un utilisateur" and search_mode == "Menu déroulant":
            # Charger seulement les top users pour le menu
            histories, user_stats = create_user_histories(df, limit_for_dropdown=True)
    
    popular_articles = get_article_popularity(df)
    
    # Métriques dataset
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_users = df['user_id'].nunique()
        st.metric("👥 Utilisateurs", f"{n_users:,}")
    with col2:
        n_articles = df['click_article_id'].nunique()
        st.metric("📰 Articles", f"{n_articles:,}")
    with col3:
        st.metric("🖱️ Interactions", f"{len(df):,}")
    with col4:
        st.metric("💾 Mode", "Sample" if use_sample else "Complet")
    
    # Info sur l'ID 0
    if 0 in df['user_id'].values:
        st.info("ℹ️ Note: Le dataset contient l'user_id 0 qui est un utilisateur valide")
    
    st.divider()
    
    # ========== COLONNES PRINCIPALES ==========
    col_user, col_results = st.columns([1, 1])
    
    # ========== COLONNE GAUCHE: User + Historique ==========
    with col_user:
        st.subheader("👤 Utilisateur et Historique")
        
        if user_mode == "Rechercher un utilisateur":
            
            # Sélection par ID ou menu déroulant
            if search_mode == "Par ID":
                # Permettre l'ID 0
                user_id_input = st.number_input(
                    "ID utilisateur",
                    min_value=0,  # Accepter 0
                    max_value=999999,
                    value=1,
                    step=1,
                    key="search_user_id"
                )
                
                # Pour le dataset complet, charger à la demande
                if not use_sample:
                    history, stats = load_user_history_by_id(user_id_input, use_sample)
                    if stats:
                        user_stats[str(user_id_input)] = stats
                        histories[str(user_id_input)] = history
                
                user_id_str = str(user_id_input)
                
            else:  # Menu déroulant
                if not histories:
                    st.warning("⚠️ Chargement des utilisateurs...")
                    histories, user_stats = create_user_histories(df, limit_for_dropdown=True)
                
                # Trier les utilisateurs par activité
                sorted_users = sorted(
                    histories.keys(),
                    key=lambda x: user_stats[x]['n_clicks'],
                    reverse=True
                )
                
                # Créer les labels avec profils
                user_options = []
                user_labels = []
                for uid in sorted_users:
                    n_clicks = user_stats[uid]['n_clicks']
                    profile, icon = get_user_profile(n_clicks)
                    user_options.append(uid)
                    user_labels.append(f"{icon} User {uid} ({n_clicks} clics - {profile})")
                
                if user_options:
                    selected_idx = st.selectbox(
                        "Sélectionner un utilisateur",
                        range(len(user_options)),
                        format_func=lambda x: user_labels[x]
                    )
                    user_id_str = user_options[selected_idx]
                    user_id_input = int(user_id_str)
                else:
                    st.error("Aucun utilisateur disponible")
                    return
            
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
                
                # Affichage de l'historique avec gestion des longs historiques
                st.write(f"**Total: {len(history)} articles**")
                
                # Bouton de recommandation
                if st.button("🚀 Générer des recommandations", type="primary", use_container_width=True):
                    with col_results:
                        generate_recommendations(user_id_input, history, n_recommendations)
                        
            else:
                st.warning(f"⚠️ Utilisateur {user_id_input} non trouvé dans le dataset")
                
                if st.checkbox("Utiliser comme nouvel utilisateur (cold start)"):
                    history = []
                    if st.button("🚀 Générer des recommandations", type="primary", use_container_width=True):
                        with col_results:
                            generate_recommendations(user_id_input, history, n_recommendations)
        
        elif user_mode == "Utilisateur aléatoire":
            st.info("🎲 Sélection aléatoire")
            
            if st.button("🎲 Tirer un utilisateur au sort", use_container_width=True):
                # Pour le sample, utiliser la liste existante
                if use_sample and histories:
                    random_uid = random.choice(list(histories.keys()))
                else:
                    # Pour le dataset complet, tirer un ID aléatoire
                    all_users = df['user_id'].unique()
                    random_uid = str(random.choice(all_users))
                
                st.session_state['random_user'] = random_uid
            
            if 'random_user' in st.session_state:
                user_id_str = st.session_state['random_user']
                user_id_input = int(user_id_str)
                
                # Charger l'historique si nécessaire
                if user_id_str not in histories:
                    history, stats = load_user_history_by_id(user_id_input, use_sample)
                    if stats:
                        user_stats[user_id_str] = stats
                        histories[user_id_str] = history
                
                if user_id_str in histories:
                    history = histories[user_id_str]
                    n_clicks = user_stats[user_id_str]['n_clicks']
                    profile_name, profile_icon = get_user_profile(n_clicks)
                    
                    st.success(f"✅ User {user_id_input} sélectionné")
                    st.info(f"{profile_icon} **Profil: {profile_name}**")
                    st.write(f"**{n_clicks} articles consultés**")
                    
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

if __name__ == "__main__":
    main()