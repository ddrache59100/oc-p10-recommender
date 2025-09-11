# 🚀 Système de Recommandation d'Articles - My Content

Projet de système de recommandation hybride utilisant des techniques de Content-Based Filtering et Collaborative Filtering, déployé sur Azure Functions avec Blob Storage.

## 📊 Aperçu du projet

Ce projet implémente un système de recommandation d'articles pour une plateforme média, capable de :
- Gérer 322,897 utilisateurs et 364,047 articles
- Traiter 2,9M de clics sur 15 jours
- Fournir des recommandations personnalisées en <100ms
- S'adapter au profil utilisateur (cold start, moderate, active)

## 🏗️ Architecture

### Système hybride
- **Content-Based (CB)** : PCA-50, similarité cosinus (69MB)
- **Collaborative Filtering (CF)** : SVD, factorisation matricielle (231MB)
- **Stratégie adaptative** :
  - Cold start (≤5 interactions) : 100% CB
  - Moderate (6-15 interactions) : 70% CB + 30% CF
  - Active (>15 interactions) : 30% CB + 70% CF

### Infrastructure Azure
- **Azure Functions** : API serverless
- **Azure Blob Storage** : Stockage des modèles (300MB total)
- **Application Insights** : Monitoring
- **Streamlit Web App** : Interface utilisateur

## 📁 Structure du projet

```
.
├── notebooks/                    # Analyse et modélisation
│   ├── 01_exploration.ipynb    # Analyse exploratoire
│   ├── 02_content_based_recommender.ipynb
│   ├── 03_collaborative_filtering.ipynb
│   ├── 04_hybrid_recommender.ipynb
│   └── models/                 # Modèles sauvegardés
│       ├── blob_cb_pca50.pkl   # Content-Based (69MB)
│       ├── blob_cf_svd.pkl     # Collaborative (231MB)
│       └── blob_metadata.pkl   # Configuration
│
├── azure_functions/             # API serverless
│   └── RecommendationFunction/
│       ├── __init__.py         # API hybride
│       └── function.json       # Configuration
│
├── streamlit_app/              # Interface utilisateur
│   ├── app.py                 # Version 1
│   └── app2.py                # Version 2
│
└── azurite-data/              # Stockage local pour tests
```

## 🚀 Installation

### Prérequis
- Python 3.10+
- Conda (recommandé)
- Azure Functions Core Tools
- Node.js 14+ (pour Azurite)
- Compte Azure actif

### Configuration de l'environnement

```bash
# Cloner le repository
git clone https://github.com/ddrache59100/oc-p10-recommender.git
cd oc-p10-recommender

# Créer environnement conda
conda create -n azure-local python=3.10
conda activate azure-local

# Installer les dépendances Python
pip install -r requirements.txt

# Installer Azurite (émulateur Blob Storage)
npm install -g azurite

# Installer Azure Functions Core Tools
# Sur Ubuntu/Debian:
curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/microsoft-ubuntu-$(lsb_release -cs)-prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list'
sudo apt-get update
sudo apt-get install azure-functions-core-tools-4
```

## 🔧 Tests en local

### 1. Démarrer le stockage Blob local (Terminal 1)
```bash
azurite-blob --silent --location ./azurite-data
```

### 2. Uploader les modèles (Terminal 2)
```bash
conda activate azure-local
cd notebooks/models
python upload_to_azurite.py
```

### 3. Lancer l'API Azure Functions (Terminal 3)
```bash
conda activate azure-local
cd azure_functions
func start
```

### 4. Tester l'API (Terminal 4)
```bash
# Test Cold Start
curl -X POST http://localhost:7071/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "history": [10, 20, 30], "n_recommendations": 5}'

# Test Moderate
curl -X POST http://localhost:7071/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2, "history": [10,20,30,40,50,60,70,80], "n_recommendations": 5}'

# Test Active
curl -X POST http://localhost:7071/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": 3, "history": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20], "n_recommendations": 5}'
```

## 📊 Résultats en production

### Métriques de performance
| Métrique | Valeur |
|----------|--------|
| Diversité | 97% |
| Coverage | 97 articles uniques |
| Performance API | ~110ms premier appel, <1ms avec cache |
| Taux de succès | 100% des utilisateurs |
| Cold start géré | 55.9% des utilisateurs |
| Taille modèles | 300MB total dans Blob Storage |

### URLs de production
- **API**: https://func-oc-p10-recommender.azurewebsites.net/api/recommend
- **Streamlit**: https://app-oc-p10-recommender-streamlit.azurewebsites.net

### Distribution des utilisateurs
- Cold start (≤5 clics) : 55.9%
- Moderate (6-15 clics) : 28.9%
- Active (>15 clics) : 15.2%

## ☁️ Architecture déployée sur Azure

### Ressources Azure utilisées
- **Resource Group**: rg-p10-recommender
- **Storage Account**: stp10rec2025 (West Europe)
- **Function App**: func-oc-p10-recommender (France Central)
- **App Service**: app-oc-p10-recommender-streamlit (West Europe)
- **Application Insights**: Monitoring intégré
- **Blob Container**: recommendation-models

### Modèles dans Blob Storage
```
recommendation-models/
├── models/cb_pca50.pkl (69.4 MB)
├── models/cf_svd.pkl (231.0 MB)
└── config/metadata.pkl (<1 MB)
```

## 📚 Documentation technique

### Notebooks
1. **01_exploration.ipynb** : Analyse des données, sparsité (99.98%), distributions
2. **02_content_based_recommender.ipynb** : Implémentation CB avec PCA, réduction 364k→50 dimensions
3. **03_collaborative_filtering.ipynb** : SVD et ALS, gestion sparsité extrême
4. **04_hybrid_recommender.ipynb** : Fusion adaptative, déploiement Blob Storage

### API Endpoints
```
POST /api/recommend
{
  "user_id": 123,
  "history": [article_ids],
  "n_recommendations": 5
}
```

Réponse :
```json
{
  "status": "success",
  "user_id": 123,
  "strategy": "moderate",
  "weights": {"cb": 0.7, "cf": 0.3},
  "recommendations": [
    {"article_id": 456, "score": 0.89, "method": "content_based"},
    ...
  ],
  "inference_time_ms": 110.8
}
```

## 🧪 Technologies utilisées

### Data Science
- **numpy 1.26.4** : Calculs matriciels
- **pandas 2.0.3** : Manipulation des données
- **scikit-learn 1.3.0** : PCA, métriques
- **scikit-surprise 1.1.4** : SVD pour collaborative filtering
- **mlflow** : Tracking des expériences (80+ runs)

### Cloud & Déploiement
- **Azure Functions** : Serverless computing
- **Azure Blob Storage** : Stockage des modèles
- **Streamlit** : Interface web
- **Azurite** : Émulateur Blob Storage local

## 🔮 Évolutions futures

- [ ] Intégration de Deep Learning (BERT embeddings)
- [ ] Système de feedback temps réel
- [ ] A/B testing framework
- [ ] API GraphQL
- [ ] Mise à jour incrémentale des modèles
- [ ] Support multi-langue
- [ ] Cache Redis distribué

## 🔧 Troubleshooting

### Problème : "No module named 'surprise'"
```bash
pip install scikit-surprise==1.1.4
```

### Problème : Azurite connection error
Vérifier qu'Azurite est lancé sur le port 10000 :
```bash
netstat -an | grep 10000
```

### Problème : Modèles trop gros pour GitHub
Les modèles utilisent Git LFS. Si problème :
```bash
git lfs install
git lfs pull
```

## 📂 Données

Les données proviennent du dataset public Globo.com (non incluses dans ce repo) :
- **Source** : [Globo.com News Dataset](https://www.kaggle.com/gspmoreira/news-portal-user-interactions-by-globocom)
- **Période** : 16 jours d'octobre 2017
- **Volume** : 2.9M interactions, 322K users, 364K articles
- **Téléchargement** : Les données doivent être placées dans `notebooks/data/`

## 👨‍💻 Auteur

**Didier DRACHE**  
Formation Data Scientist - OpenClassrooms  
Projet 10 : Système de Recommandation  
Septembre 2025

GitHub : [@ddrache59100](https://github.com/ddrache59100)

## 🙏 Remerciements

- **OpenClassrooms** pour le cadre pédagogique
- **Globo.com** pour le dataset public
- **Microsoft Azure** pour l'infrastructure cloud
- **Mon mentor OC** Sitou AFANOU pour le suivi et les conseils

---

## 📝 Licence

Ce projet est réalisé dans le cadre de la formation Data Scientist d'OpenClassrooms.

---

*Dernière mise à jour : Septembre 2025*
