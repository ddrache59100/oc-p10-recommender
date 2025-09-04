import logging
import json
import azure.functions as func
from pathlib import Path
import sys

# Ajouter le chemin vers shared
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import corrigé
from shared.recommendation_api import RealRecommendationAPI

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Recommendation function triggered')
    
    try:
        # Récupérer user_id
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
        
        # Récupérer l'historique
        user_history = []
        try:
            body = req.get_json()
            user_history = body.get('history', [])
        except:
            pass
        
        # Chemin du modèle
        model_path = Path(__file__).parent.parent / "models" / "hybrid_azure.pkl"
        
        # Utiliser RealRecommendationAPI
        api = RealRecommendationAPI(str(model_path))
        
        # Générer les recommandations
        result = api.recommend(
            user_id=int(user_id),
            user_history=user_history,
            n_recommendations=5
        )
        
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