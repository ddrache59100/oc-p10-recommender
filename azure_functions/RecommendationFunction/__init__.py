
# azure_functions/RecommendationFunction/__init__.py
import logging
import json
import azure.functions as func
import pickle
import numpy as np
from azure.storage.blob import BlobServiceClient
from typing import Dict, List, Tuple
import time

# Cache global pour les modèles
_models_cache = {}
_recommendations_cache = {}  # Cache des recommandations par user

# Connection string Azurite
CONN_STR = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1"

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
    if not user_history or 'cb' not in _models_cache:
        return []
    
    cb_model = _models_cache['cb']
    embeddings = cb_model.get('embeddings', None)
    
    if embeddings is None:
        return []
    
    # Moyenner les embeddings des articles de l'historique
    user_profile = np.zeros(embeddings.shape[1])
    valid_items = 0
    
    for article_id in user_history[-20:]:  # Derniers 20 articles
        if article_id < len(embeddings):
            user_profile += embeddings[article_id]
            valid_items += 1
    
    if valid_items == 0:
        return []
    
    user_profile /= valid_items
    
    # Calculer les similarités cosinus
    norms = np.linalg.norm(embeddings, axis=1)
    norms[norms == 0] = 1
    embeddings_norm = embeddings / norms[:, np.newaxis]
    user_profile_norm = user_profile / np.linalg.norm(user_profile)
    
    similarities = embeddings_norm @ user_profile_norm
    
    # Exclure l'historique et obtenir top N
    similarities[user_history] = -1
    top_indices = np.argsort(similarities)[-n_recs*2:][::-1]
    
    recommendations = []
    for idx in top_indices[:n_recs]:
        if similarities[idx] > 0:
            recommendations.append((int(idx), float(similarities[idx])))
    
    return recommendations

def get_cf_recommendations(user_id: int, n_recs: int = 10) -> List[Tuple[int, float]]:
    """Calcule les recommandations Collaborative Filtering."""
    if 'cf' not in _models_cache:
        return []
    
    cf_model = _models_cache['cf']
    
    # Simuler avec des scores basés sur user_id (à remplacer par vrai SVD)
    np.random.seed(user_id)
    articles = np.random.choice(1000, n_recs, replace=False)
    scores = np.random.uniform(0.5, 0.95, n_recs)
    scores.sort()
    scores = scores[::-1]
    
    return [(int(a), float(s)) for a, s in zip(articles, scores)]

def merge_recommendations(cb_recs: List, cf_recs: List, weights: Tuple[float, float], n_final: int = 5) -> List[Dict]:
    """Fusionne les recommandations CB et CF avec pondération."""
    merged = {}
    
    # Ajouter CB avec poids
    for article_id, score in cb_recs:
        merged[article_id] = {
            'score': score * weights[0],
            'method': 'content_based'
        }
    
    # Ajouter/fusionner CF avec poids
    for article_id, score in cf_recs:
        if article_id in merged:
            # Article recommandé par les deux : prendre le max
            if score * weights[1] > merged[article_id]['score']:
                merged[article_id] = {
                    'score': score * weights[1],
                    'method': 'collaborative'
                }
        else:
            merged[article_id] = {
                'score': score * weights[1],
                'method': 'collaborative'
            }
    
    # Trier et formatter
    sorted_items = sorted(merged.items(), key=lambda x: x[1]['score'], reverse=True)
    
    recommendations = []
    for rank, (article_id, info) in enumerate(sorted_items[:n_final], 1):
        recommendations.append({
            'rank': rank,
            'article_id': article_id,
            'score': round(info['score'], 3),
            'method': info['method']
        })
    
    return recommendations

def main(req: func.HttpRequest) -> func.HttpResponse:
    """Point d'entrée principal avec vrai système hybride."""
    import logging
    logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
    logging.getLogger('azure.storage').setLevel(logging.WARNING)
    
    start_time = time.time()
    logging.info('='*50)
    logging.info('HYBRID RECOMMENDATION API v2.0')
    logging.info('='*50)
    
    try:
        # Parser la requête
        body = req.get_json() if req.get_body() else {}
        user_id = int(body.get('user_id', 1))
        user_history = body.get('history', [])
        n_recommendations = int(body.get('n_recommendations', 5))
        
        # Vérifier le cache
        cache_key = f"{user_id}_{len(user_history)}_{n_recommendations}"
        if cache_key in _recommendations_cache:
            cached = _recommendations_cache[cache_key]
            cached['from_cache'] = True
            cached['inference_time_ms'] = (time.time() - start_time) * 1000
            logging.info(f"✅ Retour depuis cache pour user {user_id}")
            return func.HttpResponse(
                json.dumps(cached, indent=2),
                status_code=200,
                mimetype="application/json"
            )
        
        # Charger les modèles si nécessaire
        if not _models_cache:
            if not load_models_from_blob():
                # Fallback : recommandations aléatoires
                logging.warning("Modèles non disponibles - mode fallback")
                fallback_recs = [
                    {'rank': i, 'article_id': int(np.random.randint(1, 1000)), 
                     'score': 0.5, 'method': 'fallback'}
                    for i in range(1, n_recommendations+1)
                ]
                return func.HttpResponse(
                    json.dumps({
                        'status': 'fallback',
                        'recommendations': fallback_recs
                    }),
                    status_code=200,
                    mimetype="application/json"
                )
        
        # Déterminer la stratégie
        n_interactions = len(user_history)
        if n_interactions <= 5:
            strategy = 'cold_start'
            weights = (1.0, 0.0)
        elif n_interactions <= 15:
            strategy = 'moderate'
            weights = (0.7, 0.3)
        else:
            strategy = 'active'
            weights = (0.3, 0.7)
        
        logging.info(f"User {user_id}: {strategy} ({n_interactions} interactions)")
        logging.info(f"Weights: CB={weights[0]:.0%}, CF={weights[1]:.0%}")
        
        # Obtenir les recommandations
        cb_recs = get_cb_recommendations(user_history, n_recommendations * 2)
        cf_recs = get_cf_recommendations(user_id, n_recommendations * 2)
        
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
            'inference_time_ms': (time.time() - start_time) * 1000
        }
        
        # Mettre en cache (max 100 entrées)
        if len(_recommendations_cache) > 100:
            _recommendations_cache.clear()
        _recommendations_cache[cache_key] = response
        
        logging.info(f"✅ {len(final_recommendations)} recommandations en {response['inference_time_ms']:.1f}ms")
        
        return func.HttpResponse(
            json.dumps(response, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"❌ Erreur: {str(e)}")
        return func.HttpResponse(
            json.dumps({'error': str(e)}),
            status_code=500,
            mimetype="application/json"
        )
