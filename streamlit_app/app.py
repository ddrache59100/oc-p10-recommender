"""
My Content Recommender - Interface Streamlit
Application de démonstration du système de recommandation hybride
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
    if n_articles <= COLD_START_THRESHOLD:
        return "Cold Start", "🆕"
    elif n_articles <= ACTIVE_THRESHOLD:
        return "Moderate", "📊"
    else:
        return "Active", "🔥"

def get_strategy_info(n_articles: int) -> Dict:
    """Retourne les informations de stratégie selon le profil."""
    if n_articles <= COLD_START_THRESHOLD:
        return {
            "strategy": "cold_start",
            "weights": {"cb": 1.0, "cf": 0.0},
            "description": "100% Content-Based (utilisateur nouveau)",
            "method": "Similarité cosinus sur embeddings PCA-50"
        }
    elif n_articles <= ACTIVE_THRESHOLD:
        return {
            "strategy": "moderate",
            "weights": {"cb": 0.7, "cf": 0.3},
            "description": "70% Content-Based + 30% Collaborative",
            "method": "Hybride pondéré (CB dominant)"
        }
    else:
        return {
            "strategy": "active",
            "weights": {"cb": 0.3, "cf": 0.7},
            "description": "30% Content-Based + 70% Collaborative",
            "method": "Hybride pondéré (CF dominant avec SVD)"
        }

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

# --- Interface principale ---

def main():
    # Titre
    st.title("🎯 My Content Recommender")
    st.markdown("**Système de recommandation hybride** : Content-Based + Collaborative Filtering")
    
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
                # Compatibilité avec différentes versions de Streamlit
                if hasattr(st, 'rerun'):
                    st.rerun()
                else:
                    st.experimental_rerun()
        
        st.divider()
        
        # Source de données
        data_mode = st.radio(
            "📂 Source de données",
            ["Sample (707 users)", "Complet (322k users)"],
            index=0,
            help="Sample pour tests rapides, Complet pour production"
        )
        use_sample = "Sample" in data_mode
        
        # Paramètres
        n_recommendations = st.slider(
            "📚 Nombre de recommandations",
            min_value=1,
            max_value=20,
            value=5,
            step=1
        )
        
        st.divider()
        
        # Informations sur les stratégies
        with st.expander("ℹ️ Stratégies de recommandation"):
            st.markdown("""
            ### 🎯 Système Hybride Adaptatif
            
            **Cold Start (≤5 clics)**
            - 100% Content-Based
            - Similarité cosinus sur PCA-50
            - Embeddings de 364k articles
            
            **Moderate (6-15 clics)**
            - 70% CB + 30% CF
            - Fusion pondérée
            - Personnalisation progressive
            
            **Active (>15 clics)**
            - 30% CB + 70% CF
            - SVD pour Collaborative
            - Personnalisation maximale
            """)
        
        # Stats du système
        with st.expander("📊 Statistiques du système"):
            st.markdown("""
            - **Modèles**: CB (69MB) + CF (231MB)
            - **Stockage**: Azure Blob Storage
            - **Performance**: ~110ms (sans cache)
            - **Cache**: <1ms (après 1er appel)
            - **Couverture**: 100% des users
            """)
    
    # ========== CONTENU PRINCIPAL ==========
    
    # Chargement des données
    df, status = load_click_data(use_sample)
    
    if status == "error" or df.empty:
        st.error("Impossible de charger les données")
        return
    
    histories, user_stats = create_user_histories(df)
    popular_articles = get_article_popularity(df)
    
    # Statistiques du dataset
    st.info(f"""
    📊 **Dataset {'sample' if use_sample else 'complet'}** : 
    {len(user_stats):,} utilisateurs • {df['click_article_id'].nunique():,} articles • {len(df):,} clics
    """)
    
    # Colonnes principales
    col_input, col_results = st.columns([1, 2])
    
    # ========== COLONNE GAUCHE: Sélection utilisateur ==========
    with col_input:
        st.subheader("👤 Sélection utilisateur")
        
        selection_mode = st.radio(
            "Mode de sélection",
            ["Utilisateur existant", "Utilisateur aléatoire", "Nouvel utilisateur"],
            index=0
        )
        
        if selection_mode == "Utilisateur existant":
            # Liste des utilisateurs disponibles
            user_ids = sorted([int(uid) for uid in user_stats.keys()])
            
            # Choix entre menu déroulant ou saisie directe
            input_method = st.radio(
                "Méthode de sélection",
                ["Menu déroulant (Top 300)", "Saisie directe (ID)"],
                index=0
            )
            
            if input_method == "Menu déroulant (Top 300)":
                # Limiter à 300 pour le menu déroulant
                display_ids = user_ids[:300] if len(user_ids) > 300 else user_ids
                user_id = st.selectbox(
                    "Choisir un utilisateur",
                    display_ids,
                    format_func=lambda x: f"User {x} ({user_stats[str(x)]['n_clicks']} clics)"
                )
            else:
                # Saisie directe pour n'importe quel ID
                user_id = st.number_input(
                    "Entrer l'ID utilisateur",
                    min_value=min(user_ids),
                    max_value=max(user_ids),
                    value=user_ids[0],
                    step=1,
                    help=f"ID disponibles : {min(user_ids)} à {max(user_ids)}"
                )
                
                # Vérifier que l'ID existe
                if str(user_id) not in user_stats:
                    st.error(f"❌ L'utilisateur {user_id} n'existe pas")
                    st.info(f"IDs valides : {min(user_ids)} à {max(user_ids)}")
                    return
            
            # Récupérer l'historique
            history = histories[str(user_id)]
            
            # Afficher les stats
            profile_name, profile_icon = get_user_profile(len(history))
            strategy_info = get_strategy_info(len(history))
            
            st.success(f"{profile_icon} **{profile_name}**")
            st.caption(f"📚 {len(history)} articles consultés")
            st.caption(f"🎯 {strategy_info['description']}")
            
            # Afficher l'historique
            with st.expander(f"📜 Historique ({len(history)} articles)", expanded=False):
                st.write(history[:20])
                if len(history) > 20:
                    st.caption(f"... et {len(history)-20} autres")
            
            # Bouton de recommandation
            if st.button("🚀 Générer des recommandations", type="primary", use_container_width=True):
                with col_results:
                    generate_recommendations(user_id, history, n_recommendations)
        
        elif selection_mode == "Utilisateur aléatoire":
            # Sélection aléatoire par profil
            profile_choice = st.selectbox(
                "Choisir un profil",
                ["Aléatoire total", "Cold Start (≤5)", "Moderate (6-15)", "Active (>15)"]
            )
            
            # Filtrer selon le profil
            if profile_choice == "Cold Start (≤5)":
                candidates = [uid for uid, stats in user_stats.items() 
                            if stats['n_clicks'] <= COLD_START_THRESHOLD]
            elif profile_choice == "Moderate (6-15)":
                candidates = [uid for uid, stats in user_stats.items() 
                            if COLD_START_THRESHOLD < stats['n_clicks'] <= ACTIVE_THRESHOLD]
            elif profile_choice == "Active (>15)":
                candidates = [uid for uid, stats in user_stats.items() 
                            if stats['n_clicks'] > ACTIVE_THRESHOLD]
            else:
                candidates = list(user_stats.keys())
            
            if st.button("🎲 Sélectionner aléatoirement", use_container_width=True):
                if candidates:
                    user_id = int(random.choice(candidates))
                    history = histories[str(user_id)]
                    
                    profile_name, profile_icon = get_user_profile(len(history))
                    strategy_info = get_strategy_info(len(history))
                    
                    st.success(f"Utilisateur **{user_id}** sélectionné")
                    st.info(f"{profile_icon} **{profile_name}** • {len(history)} clics")
                    st.caption(f"🎯 {strategy_info['description']}")
                    
                    # Générer automatiquement
                    with col_results:
                        generate_recommendations(user_id, history, n_recommendations)
                else:
                    st.warning("Aucun utilisateur dans cette catégorie")
        
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
                    strategy_info = get_strategy_info(len(history))
                    st.success(f"✅ {len(history)} articles → {profile_icon} {profile_name}")
                    st.caption(f"🎯 {strategy_info['description']}")
            else:
                history = []
                st.info("🆕 Mode Cold Start (100% Content-Based)")
            
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
    
    # Déterminer la stratégie attendue
    strategy_info = get_strategy_info(len(history))
    profile_name, profile_icon = get_user_profile(len(history))
    
    # Timer et appel API
    start_time = time.time()
    with st.spinner("🔮 Génération des recommandations..."):
        result = call_recommendation_api(user_id, history, n_recommendations)
    total_time = (time.time() - start_time) * 1000
    
    # Affichage des résultats
    if result.get('status') == 'success':
        st.success(f"✅ **{len(result['recommendations'])} recommandations générées**")
        
        # Métriques en 3 colonnes
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("⏱️ Temps API", f"{result.get('inference_time_ms', 0):.1f}ms")
        with col_b:
            st.metric("📡 Temps total", f"{total_time:.1f}ms")
        with col_c:
            cache_icon = "✅ Oui" if result.get('from_cache') else "❌ Non"
            st.metric("💾 Cache", cache_icon)
        
        # Stratégie utilisée
        st.info(f"""
        **Stratégie**: {result.get('strategy', strategy_info['strategy'])} {profile_icon}  
        **Méthode**: {strategy_info['method']}  
        **Pondération**: CB {result.get('weights', strategy_info['weights'])['cb']:.0%} / CF {result.get('weights', strategy_info['weights'])['cf']:.0%}
        """)
        
        # Recommandations avec détails
        st.write("### 🎯 Articles recommandés")
        
        for rec in result['recommendations']:
            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
            with col1:
                st.write(f"**#{rec.get('rank', rec.get('article_id'))}**")
            with col2:
                st.write(f"Article **{rec['article_id']}**")
            with col3:
                method = rec.get('source', 'unknown')
                if method == 'content_based':
                    st.success("🔍 Content-Based")
                elif method == 'collaborative':
                    st.info("👥 Collaborative")
                else:
                    st.warning(f"📊 {method}")
            with col4:
                st.write(f"Score: **{rec['score']:.3f}**")
        
        # Score moyen et diversité
        scores = [r['score'] for r in result['recommendations']]
        avg_score = sum(scores) / len(scores) if scores else 0
        unique_methods = set(r.get('source', 'unknown') for r in result['recommendations'])
        
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("📊 Score moyen", f"{avg_score:.3f}")
        with col_stat2:
            # Gestion sûre de la diversité
            if not unique_methods:
                diversite = "N/A"
            elif len(unique_methods) > 1:
                diversite = "Hybride"
            else:
                # Conversion sûre du set en liste
                methods_list = list(unique_methods)
                diversite = methods_list[0] if methods_list else "Unknown"
            st.metric("🎨 Diversité", diversite)
        
    else:  # error
        st.error(f"❌ **Erreur**: {result.get('error', 'Erreur inconnue')}")
        
        if result.get('recommendations'):
            st.warning("⚠️ Recommandations de fallback:")
            for rec in result['recommendations']:
                st.write(f"Article {rec['article_id']}")
    
    # Détails techniques
    with st.expander("🔧 Détails JSON"):
        st.json(result)
    
    # Sauvegarder le résultat
    st.session_state['last_result'] = result

if __name__ == "__main__":
    main()