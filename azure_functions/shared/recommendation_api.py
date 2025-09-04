"""
API de recommandation RÉELLE - Pas de simulation !
"""

import pickle
import numpy as np
import time
from typing import Dict, List, Any, Optional
from pathlib import Path


class RealRecommendationAPI:
    """API de recommandation qui utilise les VRAIS historiques."""
    
    def __init__(self, model_path: str):
        """Charge le modèle avec embeddings."""
        print(f"Chargement du modèle depuis {model_path}")
        
        with open(model_path, 'rb') as f:
            self.model_data = pickle.load(f)
        
        self.cb_model = self.model_data.get('cb_model', {})
        self.fallback_articles = self.model_data.get('fallback_articles', {})
        
        # Embeddings OBLIGATOIRES
        if self.cb_model and 'embeddings' in self.cb_model:
            self.embeddings = self.cb_model['embeddings']
            print(f"✅ Embeddings: {self.embeddings.shape}")
            # Pré-calculer les normes pour la similarité cosinus
            self.embeddings_norm = self.embeddings / (np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-8)
        else:
            raise ValueError("❌ ERREUR: Pas d'embeddings dans le modèle!")
        
        self.cache = {}
        self.stats = {'total_requests': 0, 'cache_hits': 0, 'errors': 0}
    
    def recommend(self, 
                  user_id: int,
                  user_history: List[int],
                  n_recommendations: int = 5,
                  exclude_seen: bool = True) -> Dict[str, Any]:
        """
        Génère des recommandations basées sur l'HISTORIQUE RÉEL.
        
        Args:
            user_id: ID de l'utilisateur
            user_history: Liste RÉELLE des article_ids consultés/cliqués
            n_recommendations: Nombre de recommandations
            exclude_seen: Si True, exclut les articles déjà vus
        
        Returns:
            Dict avec les recommandations
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        # Validation
        if not user_history or len(user_history) == 0:
            # Utilisateur sans historique = recommander les populaires
            return self._get_popular_recommendations(user_id, n_recommendations)
        
        # Cache
        cache_key = f"{user_id}_{hash(tuple(user_history))}_{n_recommendations}"
        if cache_key in self.cache:
            self.stats['cache_hits'] += 1
            cached = self.cache[cache_key].copy()
            cached['from_cache'] = True
            return cached
        
        try:
            # CALCUL RÉEL du profil utilisateur
            valid_articles = [a for a in user_history if a < len(self.embeddings)]
            if not valid_articles:
                return self._get_popular_recommendations(user_id, n_recommendations)
            
            # Moyenne des embeddings des articles RÉELLEMENT vus
            user_profile = np.mean(self.embeddings[valid_articles], axis=0)
            user_profile_norm = user_profile / (np.linalg.norm(user_profile) + 1e-8)
            
            # Similarité cosinus avec TOUS les articles
            similarities = np.dot(self.embeddings_norm, user_profile_norm)
            
            # Exclure les articles déjà vus si demandé
            if exclude_seen:
                similarities[valid_articles] = -1
            
            # Sélectionner les TOP N
            top_indices = np.argsort(similarities)[::-1][:n_recommendations]
            
            # Construire les recommandations
            recommendations = []
            for rank, idx in enumerate(top_indices, 1):
                if similarities[idx] > 0:
                    recommendations.append({
                        'rank': rank,
                        'article_id': int(idx),
                        'score': float(similarities[idx]),
                        'method': 'content_based_real'
                    })
            
            # Résultat
            result = {
                'status': 'success',
                'user_id': user_id,
                'n_history': len(user_history),
                'n_valid_articles': len(valid_articles),
                'recommendations': recommendations,
                'inference_time_ms': round((time.time() - start_time) * 1000, 2),
                'from_cache': False
            }
            
            # Cache (limite 1000)
            if len(self.cache) < 1000:
                self.cache[cache_key] = result.copy()
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            return {
                'status': 'error',
                'user_id': user_id,
                'error': str(e),
                'recommendations': self._get_popular_fallback(n_recommendations),
                'inference_time_ms': round((time.time() - start_time) * 1000, 2)
            }
    
    def _get_popular_recommendations(self, user_id: int, n: int) -> Dict[str, Any]:
        """Recommandations populaires pour cold start."""
        recommendations = []
        
        if self.fallback_articles:
            sorted_articles = sorted(
                self.fallback_articles.items(),
                key=lambda x: x[1],
                reverse=True
            )[:n]
            
            for rank, (article_id, count) in enumerate(sorted_articles, 1):
                recommendations.append({
                    'rank': rank,
                    'article_id': int(article_id),
                    'score': float(1.0 - rank * 0.05),
                    'method': 'popular'
                })
        
        return {
            'status': 'cold_start',
            'user_id': user_id,
            'recommendations': recommendations,
            'inference_time_ms': 0.5,
            'from_cache': False
        }
    
    def _get_popular_fallback(self, n: int) -> List[Dict]:
        """Articles populaires comme fallback."""
        recommendations = []
        if self.fallback_articles:
            for rank, (article_id, _) in enumerate(list(self.fallback_articles.items())[:n], 1):
                recommendations.append({
                    'rank': rank,
                    'article_id': int(article_id),
                    'score': 0.5,
                    'method': 'fallback'
                })
        return recommendations
    
    def get_stats(self) -> Dict[str, Any]:
        """Statistiques d'utilisation."""
        return self.stats


# Point d'entrée Azure Functions
def main(req):
    """Handler pour Azure Functions."""
    import json
    
    # Parser la requête
    user_id = req.params.get('user_id')
    user_history = req.get_json().get('history', [])
    n_recommendations = req.params.get('n', 5)
    
    # Charger l'API
    api = RealRecommendationAPI("models/hybrid_azure.pkl")
    
    # Générer les recommandations
    result = api.recommend(
        user_id=int(user_id),
        user_history=user_history,
        n_recommendations=int(n_recommendations)
    )
    
    return json.dumps(result)
