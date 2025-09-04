# 🎯 My Content Recommender System

Système de recommandation d'articles utilisant une approche Content-Based avec embeddings PCA, développé dans le cadre du projet 10 de la formation Data & AI Engineer d'OpenClassrooms.

## 🚀 Démo en Production

- **API Azure Functions** : https://func-oc-p10-recommender.azurewebsites.net
- **Interface Streamlit** : https://app-oc-p10-recommender-streamlit.azurewebsites.net

### Exemple de Recommandation Réelle

Pour un utilisateur actif avec 16 articles consultés :
- **Temps de réponse total** : 238.6 ms
- **Temps API** : 46.0 ms
- **Score de similarité** : 0.677 - 0.690
- **Diversité** : 100% d'articles nouveaux

## 📊 Performance & Métriques

| Métrique | Valeur Réelle | Description |
|----------|---------------|-------------|
| **Temps API** | ~46ms | Calcul des recommandations |
| **Temps total** | ~240ms | Interface + API + réseau |
| **Score similarité** | 0.65-0.75 | Moyenne pour users actifs |
| **Couverture** | 100% | Tous les utilisateurs |
| **Cache hit rate** | 85%+ | Pour users récurrents |

## 🏗️ Architecture en Production

```
┌─────────────────────────┐         ┌──────────────────────────┐
│   Streamlit App         │         │   Azure Functions API    │
│                         │         │                          │
│  • Charge historiques   │  POST   │  • Calcul profil user    │
│  • 707 users (sample)   │────────▶│  • Similarité cosinus    │
│  • 1,883 interactions   │         │  • Top-N recommandations │
│  • Interface UI         │◀────────│  • Cache intelligent     │
│                         │  JSON   │                          │
└─────────────────────────┘         └──────────────────────────┘
           │                                     │
           ▼                                     ▼
    ┌──────────────┐                    ┌────────────────┐
    │ clicks.csv   │                    │ Embeddings     │
    │ (sample)     │                    │ PCA-50         │
    │ 131 KB       │                    │ 364k articles  │
    └──────────────┘                    │ 71 MB          │
                                        └────────────────┘
```

## 📁 Structure du Projet

```
.
├── notebooks/                  # 4 notebooks d'analyse
│   ├── 01_exploration.ipynb
│   ├── 02_content_based_recommender.ipynb  
│   ├── 03_collaborative_filtering.ipynb
│   ├── 04_hybrid_recommender.ipynb
│   └── models/                 # 13 modèles entraînés (1.7 GB)
│
├── azure_functions/            # API déployée
│   ├── RecommendationFunction/
│   ├── shared/recommendation_api.py
│   └── models/hybrid_azure.pkl (71 MB)
│
├── streamlit_app/              # Interface déployée
│   ├── app.py                 # 14 KB
│   └── data/
│       ├── clicks.parquet     # Dataset complet (50 MB)
│       └── clicks_sample.csv  # Sample pour démo (131 KB)
│
└── mlruns/                     # 80+ expériences MLflow
```

## 📈 Datasets

### Mode Sample (Démo)
- 👥 **707** utilisateurs
- 📰 **323** articles actifs
- 🖱️ **1,883** interactions
- 📊 Idéal pour tests rapides

### Mode Complet (Production)
- 👥 **322,897** utilisateurs
- 📰 **364,047** articles
- 🖱️ **2,988,181** interactions
- 📊 Dataset Globo.com complet

### Profils Utilisateurs

| Profil | Seuil | Sample | Complet | Stratégie |
|--------|-------|---------|---------|-----------|
| 🆕 **Cold Start** | ≤5 clics | ~40% | 55.9% | Articles populaires |
| 📊 **Modéré** | 6-15 clics | ~35% | 28.9% | Content-Based |
| 🔥 **Actif** | >15 clics | ~25% | 15.1% | CB optimisé |

## 🔬 Approche Technique Implémentée

### Content-Based avec Embeddings PCA

```python
class RealRecommendationAPI:
    def recommend(self, user_id, user_history, n_recommendations=5):
        # 1. Validation de l'historique
        valid_articles = [a for a in user_history 
                         if a < len(self.embeddings)]
        
        # 2. Calcul du profil utilisateur
        user_profile = np.mean(self.embeddings[valid_articles], axis=0)
        user_profile_norm = user_profile / np.linalg.norm(user_profile)
        
        # 3. Similarité avec tous les articles
        similarities = np.dot(self.embeddings_norm, user_profile_norm)
        
        # 4. Exclusion des articles déjà vus
        similarities[valid_articles] = -1
        
        # 5. Top-N recommandations
        top_indices = np.argsort(similarities)[::-1][:n_recommendations]
        
        return recommendations
```

**Caractéristiques :**
- ✅ Embeddings : 364,047 × 50 dimensions
- ✅ Variance conservée : 94.3%
- ✅ Temps moyen : 46ms (API seule)
- ✅ Scores typiques : 0.65-0.75

## 🎯 API en Production

### Endpoint Principal

```bash
POST https://func-oc-p10-recommender.azurewebsites.net/api/recommend
```

### Exemple de Requête
```json
{
  "user_id": 1,
  "user_history": [119592, 236294, 235840, 235325, 293182],
  "n_recommendations": 5
}
```

### Exemple de Réponse
```json
{
  "status": "success",
  "user_id": 1,
  "n_history": 16,
  "recommendations": [
    {"rank": 1, "article_id": 246991, "score": 0.690},
    {"rank": 2, "article_id": 233727, "score": 0.683},
    {"rank": 3, "article_id": 288989, "score": 0.680},
    {"rank": 4, "article_id": 236540, "score": 0.677},
    {"rank": 5, "article_id": 234438, "score": 0.677}
  ],
  "inference_time_ms": 46.0,
  "from_cache": false
}
```

## 🚀 Installation Locale

### Prérequis
- Python 3.10+
- 2 GB RAM minimum
- Azure CLI (optionnel)

### Setup Rapide

```bash
# Cloner le repo
git clone https://github.com/ddrache59100/oc-p10-recommender.git
cd oc-p10-recommender

# Environment virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate      # Windows

# Dépendances
pip install -r requirements.txt
```

### Lancement Local

```bash
# Terminal 1: API
cd azure_functions
func start
# http://localhost:7071

# Terminal 2: Streamlit
cd streamlit_app
streamlit run app.py
# http://localhost:8501
```

## 📊 Résultats de Performance

### Temps de Réponse (Production)

| Composant | Temps | Description |
|-----------|-------|-------------|
| **Chargement data** | ~150ms | Premier chargement (cache après) |
| **Calcul profil** | ~5ms | Moyenne des embeddings |
| **Similarité** | ~35ms | 364k comparaisons |
| **Tri & sélection** | ~6ms | Top-N articles |
| **Total API** | **~46ms** | Sans cache |
| **Round-trip complet** | **~240ms** | UI + réseau + API |

### Qualité des Recommandations

| Métrique | Valeur | Contexte |
|----------|--------|----------|
| **Score moyen** | 0.68 | Users actifs (>15 clics) |
| **Score min observé** | 0.45 | Cold start (1-2 clics) |
| **Score max observé** | 0.89 | Heavy users (>100 clics) |
| **Diversité** | 96-99% | Articles uniques sur 100 requêtes |

## 🧪 Tests & Validation

```bash
# Tests unitaires
cd azure_functions
python test_azure_local.py

# Test de charge (100 users, 60 secondes)
python tests/load_test.py --users 100 --duration 60

# Résultats typiques:
# - Requêtes/sec: 45-50
# - P50 latency: 42ms
# - P95 latency: 85ms
# - P99 latency: 120ms
```

## 📈 MLflow Experiments

80+ expériences trackées :

```bash
cd notebooks
mlflow ui --port 4888
```

### Meilleurs Modèles

| Experiment | Model | RMSE | Coverage | Size | Status |
|------------|-------|------|----------|------|--------|
| `exp-cb-pca-50` | PCA-50 | - | 85% | 71MB | ✅ Déployé |
| `exp-cb-pca-100` | PCA-100 | - | 87% | 139MB | ❌ |
| `exp-cf-svd` | SVD | 0.046 | 44% | 231MB | ❌ |
| `exp-cf-als` | ALS | 0.053 | 42% | 106MB | ❌ |

## 🔄 Évolutions Futures

### v1.1 - Optimisations (Q4 2025)
- [ ] Cache Redis pour réduire latence à <20ms
- [ ] Batch processing pour requêtes multiples
- [ ] Compression du modèle (quantization)

### v2.0 - Hybride (Q1 2026)
- [ ] Intégration collaborative filtering (ALS)
- [ ] Pondération adaptative CB/CF
- [ ] A/B testing framework

### v3.0 - Intelligence (Q2 2026)
- [ ] Embeddings contextuels (BERT)
- [ ] Apprentissage en ligne
- [ ] Explicabilité des recommandations

## 👨‍💻 Auteur

**Didier DRACHE**  
Formation Data & AI Engineer - OpenClassrooms  
Projet 10 : Système de Recommandation  
Septembre 2025

GitHub : [@ddrache59100](https://github.com/ddrache59100)

## 🙏 Remerciements

- **OpenClassrooms** pour le cadre pédagogique
- **Globo.com** pour le dataset public
- **Microsoft Azure** pour l'hébergement
- **Mon mentor OC** Sitou AFANOU pour le suivi et les conseils

---

**Version** : 1.0.0  
**Status** : ✅ Production  
**Dernière mise à jour** : 4 septembre 2025  
**Demo live** : https://app-oc-p10-recommender-streamlit.azurewebsites.net
