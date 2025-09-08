"""
Azure Function avec cache simple pour l'API existante
"""

import logging
import json
import azure.functions as func
from pathlib import Path
import sys

# Ajouter le chemin vers shared
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import de l'API existante
from shared.recommendation_api import RealRecommendationAPI

# Variables globales pour le cache et l'API
_api_instance = None
_cache = {}
_max_cache_size = 1000

def get_cache_key(user_id: int, history: list, n_reco: int) -> str:
    """Génère une clé de cache unique."""
    # Trier et limiter l'historique pour la clé
    history_sorted = sorted(history[:20]) if history else []
    history_str = ",".join(map(str, history_sorted))
    return f"{user_id}:{history_str}:{n_reco}"

def main(req: func.HttpRequest) -> func.HttpResponse:
    global _api_instance, _cache
    
    logging.info('Recommendation function triggered')
    
    try:
        # Récupérer user_id depuis la route ou le body
        user_id = req.route_params.get('user_id')
        
        if not user_id:
            try:
                body = req.get_json()
                user_id = body.get('user_id')
            except:
                pass
        
        if not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Convertir en int et valider
        try:
            user_id = int(user_id)
            if user_id < 0:
                return func.HttpResponse(
                    json.dumps({"error": "user_id must be >= 0"}),
                    status_code=400,
                    mimetype="application/json"
                )
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "user_id must be an integer"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Récupérer l'historique et les paramètres
        user_history = []
        n_recommendations = 5
        
        try:
            body = req.get_json()
            user_history = body.get('history', [])
            n_recommendations = body.get('n_recommendations', 5)
        except:
            pass
        
        # Vérifier le cache
        cache_key = get_cache_key(user_id, user_history, n_recommendations)
        
        if cache_key in _cache:
            logging.info(f"Cache hit for user {user_id}")
            result = _cache[cache_key].copy()
            result['from_cache'] = True
            result['inference_time_ms'] = 0.5
            return func.HttpResponse(
                json.dumps(result),
                status_code=200,
                mimetype="application/json"
            )
        
        # Charger l'API si nécessaire
        if _api_instance is None:
            model_path = Path(__file__).parent.parent / "models" / "hybrid_azure.pkl"
            
            if not model_path.exists():
                logging.error(f"Modèle non trouvé: {model_path}")
                return func.HttpResponse(
                    json.dumps({"error": "Model not found"}),
                    status_code=500,
                    mimetype="application/json"
                )
            
            logging.info("Chargement du modèle...")
            _api_instance = RealRecommendationAPI(str(model_path))
            logging.info("Modèle chargé avec succès")
        
        # Générer les recommandations
        result = _api_instance.recommend(
            user_id=user_id,
            user_history=user_history,
            n_recommendations=n_recommendations
        )
        
        # Mettre en cache si succès
        if result.get('status') == 'success':
            # Gérer la taille du cache
            if len(_cache) >= _max_cache_size:
                # Supprimer le plus ancien (simple FIFO)
                first_key = next(iter(_cache))
                del _cache[first_key]
            
            # Ajouter au cache
            _cache[cache_key] = result.copy()
            logging.info(f"Résultat mis en cache pour user {user_id}. Cache size: {len(_cache)}")
        
        # S'assurer que from_cache est False pour la première requête
        result['from_cache'] = False
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )