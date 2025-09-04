#!/usr/bin/env python3
"""
Test local de l'API Azure Functions avec vrais historiques.
"""

import sys
import json
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ajouter le chemin vers shared
sys.path.insert(0, str(Path(__file__).parent / "shared"))

from recommendation_api import RealRecommendationAPI

def test_api():
    """Test de l'API avec différents cas."""
    
    # Charger le modèle
    model_path = Path(__file__).parent / "models" / "hybrid_azure.pkl"
    if not model_path.exists():
        logger.error(f"Modèle non trouvé: {model_path}")
        return
    
    # Charger les historiques pour les tests
    histories_path = Path(__file__).parent.parent / "notebooks" / "models" / "user_histories_sample.json"
    if histories_path.exists():
        with open(histories_path, 'r') as f:
            user_histories = json.load(f)
        logger.info(f"Historiques chargés pour {len(user_histories)} utilisateurs")
    else:
        user_histories = {}
        logger.warning("Pas d'historiques trouvés - tests avec historiques vides")
    
    # Initialiser l'API
    api = RealRecommendationAPI(str(model_path))
    
    # Tests
    test_cases = [
        {
            "user_id": 1,
            "history": user_histories.get("1", []),
            "description": "User avec historique réel"
        },
        {
            "user_id": 999,
            "history": [],
            "description": "Nouvel utilisateur (cold start)"
        },
        {
            "user_id": 10,
            "history": user_histories.get("10", []),
            "description": "User actif avec grand historique"
        }
    ]
    
    print("\n" + "="*60)
    print("TESTS DE L'API")
    print("="*60)
    
    for test in test_cases:
        print(f"\n{test['description']}:")
        print(f"  User ID: {test['user_id']}")
        print(f"  Historique: {len(test['history'])} articles")
        
        if test['history'][:3]:  # Afficher les 3 premiers
            print(f"  Échantillon: {test['history'][:3]}")
        
        # Appel API
        result = api.recommend(
            user_id=test['user_id'],
            user_history=test['history'],
            n_recommendations=5
        )
        
        print(f"  Status: {result['status']}")
        print(f"  Temps: {result.get('inference_time_ms', 0):.1f}ms")
        print(f"  Recommandations: {len(result.get('recommendations', []))}")
        
        if result.get('recommendations'):
            print("  Top 3:")
            for rec in result['recommendations'][:3]:
                print(f"    - Article {rec['article_id']}: {rec['score']:.3f} ({rec['method']})")
    
    # Statistiques
    print("\n" + "="*60)
    print("STATISTIQUES")
    print("="*60)
    stats = api.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    test_api()