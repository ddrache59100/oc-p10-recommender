# azure_functions/RecommendationFunction/__init__.py
import logging
import json
import azure.functions as func
import pickle
import numpy as np
import os
from azure.storage.blob import BlobServiceClient
from typing import Dict, List, Tuple
import time
from collections import OrderedDict

# ===== IMPLEMENTATION CACHE LRU =====
class LRUCache:
    """Cache LRU (Least Recently Used) pour optimiser les performances."""
    
    def __init__(self, capacity: int = 100):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.hits = 0
        self.misses = 0
    
    def get(self, key):
        """Récupère une valeur du cache et la marque comme récemment utilisée."""
        if key not in self.cache:
            self.misses += 1
            return None
        # Déplacer en fin (plus récemment utilisé)
        self.cache.move_to_end(key)
        self.hits += 1
        return self.cache[key]
    
    def put(self, key, value):
        """Ajoute ou met à jour une valeur dans le cache."""
        if key in self.cache:
            # Mettre à jour et déplacer en fin
            self.cache.move_to_end(key)
        self.cache[key] = value
        # Si dépassement capacité, supprimer le plus ancien (LRU)
        if len(self.cache) > self.capacity:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
            logging.info(f"LRU: Éviction de l'entrée {oldest}")
    
    def clear(self):
        """Vide complètement le cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self):
        """Retourne les statistiques du cache."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'size': len(self.cache),
            'capacity': self.capacity,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate
        }

# ===== CACHES GLOBAUX AVEC LRU =====
_models_cache = {}  # Cache des modèles (pas LRU car chargés une fois)
_recommendations_cache = LRUCache(capacity=100)  # Cache LRU pour recommandations

# Connection string Azurite
CONN_STR = os.environ.get('AZURE_STORAGE_CONNECTION_STRING', 
                          "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1")


def load_models_from_blob():
    """Charge tous les modèles depuis Blob Storage."""
    global _models_cache
    
    if _models_cache:
        return True 
    
    try:
        blob_service = BlobServiceClient.from_connection_string(CONN_STR)
        container = blob_service.get_container_client("recommendation-models")
        
        # Charger CB model
        logging.info("Chargement du modèle CB...")
        blob = container.get_blob_client("models/cb_pca50.pkl")
        cb_data = blob.download_blob().readall()
        _models_cache['cb'] = pickle.loads(cb_data)
        logging.info(f"✅ CB chargé: {len(cb_data)/1024**2:.1f} MB")
        
        # Charger CF model
        logging.info("Chargement du modèle CF...")
        blob = container.get_blob_client("models/cf_svd.pkl")
        cf_data = blob.download_blob().readall()
        _models_cache['cf'] = pickle.loads(cf_data)
        logging.info(f"✅ CF chargé: {len(cf_data)/1024**2:.1f} MB")
        
        # Charger metadata
        blob = container.get_blob_client("config/metadata.pkl")
        metadata_data = blob.download_blob().readall()
        _models_cache['metadata'] = pickle.loads(metadata_data)
        logging.info("✅ Metadata chargé")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erreur chargement modèles: {str(e)}")
        return False

def get_cb_recommendations(user_history: List[int], n_recs: int = 10) -> List[Tuple[int, float]]:
    """Calcule les recommandations Content-Based."""
    if 'cb' not in _models_cache:
        return []
    
    embeddings = _models_cache['cb']['embeddings']
    
    # Créer profil utilisateur
    user_profile = np.zeros(embeddings.shape[1])
    for article_id in user_history[-20:]:  # Derniers 20 articles
        if article_id < len(embeddings):
            user_profile += embeddings[article_id]
    
    if np.sum(user_profile) == 0:
        return []
    
    user_profile = user_profile / np.linalg.norm(user_profile)
    
    # Calculer similarités
    similarities = np.dot(embeddings, user_profile)
    
    # Exclure articles déjà vus
    for article_id in user_history:
        if article_id < len(similarities):
            similarities[article_id] = -1
    
    # Top N
    top_indices = np.argsort(similarities)[-n_recs:][::-1]
    
    return [(int(idx), float(similarities[idx])) 
            for idx in top_indices if similarities[idx] > 0]

def get_cf_recommendations(user_id: int, n_recs: int = 10) -> List[Tuple[int, float]]:
    """Calcule les recommandations Collaborative Filtering."""
    if 'cf' not in _models_cache:
        return []
    
    try:
        # Pour le POC: Simuler avec des scores basés sur user_id
        # TODO: Implémenter avec vrai modèle SVD en production
        np.random.seed(user_id)
        articles = np.random.choice(1000, n_recs, replace=False)
        scores = np.random.uniform(0.3, 0.9, n_recs)
        
        return [(int(article), float(score)) 
                for article, score in zip(articles, scores)]
    except Exception as e:
        logging.error(f"Erreur CF: {str(e)}")
        return []

def merge_recommendations(
    cb_recs: List[Tuple[int, float]], 
    cf_recs: List[Tuple[int, float]], 
    weights: Tuple[float, float],
    n_final: int = 5
) -> List[Dict]:
    """Fusionne les recommandations CB et CF avec normalisation."""
    cb_weight, cf_weight = weights
    
    # Normaliser les scores CB et CF entre 0 et 1
    def normalize_scores(recs):
        if not recs:
            return []
        scores = [score for _, score in recs]
        min_score = min(scores)
        max_score = max(scores)
        if max_score == min_score:
            return [(art_id, 1.0) for art_id, _ in recs]
        return [(art_id, (score - min_score) / (max_score - min_score)) 
                for art_id, score in recs]
    
    # Normaliser avant pondération
    cb_recs_norm = normalize_scores(cb_recs)
    cf_recs_norm = normalize_scores(cf_recs)
    
    # Dictionnaire pour stocker scores et sources
    recommendations = {}
    
    # Ajouter CB avec source
    for article_id, score in cb_recs_norm:
        recommendations[article_id] = {
            'score': score * cb_weight,
            'source': 'content_based'
        }
    
    # Ajouter/fusionner CF
    for article_id, score in cf_recs_norm:
        weighted_score = score * cf_weight
        if article_id in recommendations:
            recommendations[article_id]['score'] += weighted_score
            recommendations[article_id]['source'] = 'hybrid'
        else:
            recommendations[article_id] = {
                'score': weighted_score,
                'source': 'collaborative'
            }
    
    # Trier par score
    sorted_items = sorted(
        recommendations.items(), 
        key=lambda x: x[1]['score'], 
        reverse=True
    )
    
    return [
        {
            'article_id': article_id,
            'score': float(data['score']),
            'source': data['source'],
            'rank': idx + 1
        }
        for idx, (article_id, data) in enumerate(sorted_items[:n_final])
    ]

def get_user_profile(history_length: int) -> str:
    """Détermine le profil utilisateur basé sur l'historique."""
    if history_length <= 5:
        return "cold_start"
    elif history_length <= 15:
        return "moderate"
    else:
        return "active"

def get_strategy_weights(profile: str) -> Tuple[float, float]:
    """Retourne les poids CB/CF selon le profil."""
    strategies = {
        'cold_start': (1.0, 0.0),
        'moderate': (0.7, 0.3),
        'active': (0.3, 0.7)
    }
    return strategies.get(profile, (0.5, 0.5))

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Point d'entrée de l'Azure Function.
    Gère les requêtes de recommandation avec cache LRU.
    """
    start_time = time.time()
    
    try:
        # Parser la requête
        user_id = req.params.get('user_id')
        if req.method == 'POST':
            try:
                body = req.get_json()
                user_id = user_id or body.get('user_id')
                user_history = body.get('history', [])
                n_recommendations = body.get('n_recommendations', 5)
            except:
                user_history = []
                n_recommendations = 5
        else:
            user_history = []
            n_recommendations = 5
        
        # Validation
        if user_id is None or user_id == '':
            return func.HttpResponse(
                json.dumps({'error': 'user_id required'}),
                status_code=400,
                mimetype="application/json"
            )
        
        try:
            user_id = int(user_id)
        except ValueError:
            return func.HttpResponse(
                json.dumps({'error': 'user_id must be integer'}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Créer clé de cache
        cache_key = f"{user_id}_{n_recommendations}_{len(user_history)}"
        
        # Vérifier le cache LRU
        cached_response = _recommendations_cache.get(cache_key)
        if cached_response:
            # Ajouter les stats de cache
            cached_response['from_cache'] = True
            cached_response['cache_stats'] = _recommendations_cache.get_stats()
            cached_response['response_time_ms'] = (time.time() - start_time) * 1000
            
            logging.info(f"✅ Cache HIT pour user {user_id} (hit rate: {cached_response['cache_stats']['hit_rate']:.1f}%)")
            
            return func.HttpResponse(
                json.dumps(cached_response, indent=2),
                status_code=200,
                mimetype="application/json"
            )
        
        logging.info(f"Cache MISS pour user {user_id} - Calcul des recommandations")
        
        # Charger les modèles si nécessaire
        if not load_models_from_blob():
            return func.HttpResponse(
                json.dumps({'error': 'Failed to load models'}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Déterminer le profil et la stratégie
        n_interactions = len(user_history)
        profile = get_user_profile(n_interactions)
        weights = get_strategy_weights(profile)
        cb_weight, cf_weight = weights
        
        strategy = f"{profile} (CB:{cb_weight:.0%}, CF:{cf_weight:.0%})"
        
        logging.info(f"User {user_id}: {n_interactions} interactions, stratégie: {strategy}")
        
        # Obtenir recommandations
        cb_recs = get_cb_recommendations(user_history, n_recommendations * 2) if cb_weight > 0 else []
        cf_recs = get_cf_recommendations(user_id, n_recommendations * 2) if cf_weight > 0 else []
        
        # Fusionner
        final_recommendations = merge_recommendations(
            cb_recs, cf_recs, weights, n_recommendations
        )
        
        # Construire la réponse
        response = {
            'status': 'success',
            'user_id': user_id,
            'strategy': strategy,
            'weights': {'cb': weights[0], 'cf': weights[1]},
            'n_interactions': n_interactions,
            'recommendations': final_recommendations,
            'models_loaded': list(_models_cache.keys()),
            'from_cache': False,
            'cache_stats': _recommendations_cache.get_stats(),
            'inference_time_ms': (time.time() - start_time) * 1000
        }
        
        # Mettre en cache avec LRU
        _recommendations_cache.put(cache_key, response.copy())
        
        logging.info(f"✅ {len(final_recommendations)} recommandations générées en {response['inference_time_ms']:.1f}ms")
        logging.info(f"Cache LRU: {_recommendations_cache.get_stats()}")
        
        return func.HttpResponse(
            json.dumps(response, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"❌ Erreur: {str(e)}")
        error_response = {
            'error': str(e),
            'cache_stats': _recommendations_cache.get_stats() if '_recommendations_cache' in globals() else None,
            'response_time_ms': (time.time() - start_time) * 1000
        }
        return func.HttpResponse(
            json.dumps(error_response),
            status_code=500,
            mimetype="application/json"
        )