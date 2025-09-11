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

### Infrastructure
- **Azure Functions** : API serverless
- **Azure Blob Storage** : Stockage des modèles
- **Streamlit** : Interface utilisateur
- **Azurite** : Émulateur Blob Storage local

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

### Configuration de l'environnement

```bash
# Cloner le repository
git clone https://github.com/votre-username/oc-p10-recommender.git
cd oc-p10-recommender

# Créer environnement conda
conda create -n azure-local python=3.10
conda activate azure-local

# Installer les dépendances Python
pip install -r requirements.txt
pip install scikit-surprise  # Pour Collaborative Filtering

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

## 🔧 Lancement local

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

### 5. Lancer Streamlit (optionnel)
```bash
cd streamlit_app
streamlit run app.py
```

## 📊 Résultats

### Métriques de performance
| Métrique | Valeur |
|----------|--------|
| Diversité | 97% |
| Coverage | 97 articles uniques |
| Performance API | <100ms (avec cache) |
| Taux de succès | 100% des utilisateurs |
| Cold start géré | 55.9% des utilisateurs |
| Taille modèles | 300MB total |

### Comparaison des approches
| Approche | Diversité | Performance | Cold Start | Personnalisation |
|----------|-----------|-------------|------------|------------------|
| Content-Based | 98% | 10ms | ✅ Excellent | ⚠️ Limitée |
| Collaborative | 94% | 50ms | ❌ Problème | ✅ Excellente |
| **Hybride** | **97%** | **90ms** | **✅ Géré** | **✅ Adaptative** |

### Distribution des utilisateurs
- Cold start (≤5 clics) : 55.9%
- Moderate (6-15 clics) : 28.9%
- Active (>15 clics) : 15.2%

## ☁️ Déploiement sur Azure

### Prérequis Azure
- Compte Azure actif
- Azure CLI installé
- Droits de création de ressources

### Commandes de déploiement
```bash
# Créer un groupe de ressources
az group create --name rg-recommender --location francecentral

# Créer un compte de stockage
az storage account create \
  --name strecommender \
  --resource-group rg-recommender \
  --location francecentral \
  --sku Standard_LRS

# Créer un container Blob
az storage container create \
  --name recommendation-models \
  --account-name strecommender

# Créer l'application Function
az functionapp create \
  --resource-group rg-recommender \
  --consumption-plan-location francecentral \
  --runtime python \
  --runtime-version 3.10 \
  --functions-version 4 \
  --name func-recommender \
  --storage-account strecommender

# Déployer le code
cd azure_functions
func azure functionapp publish func-recommender
```

## 🧪 Tests et validation

### Tests unitaires
```bash
pytest tests/
```

### Tests de charge
```bash
locust -f tests/load_test.py --host=http://localhost:7071
```

### Monitoring
- Application Insights pour les métriques
- Logs Azure Functions pour le debugging
- Cache hit rate > 80% attendu

## 📚 Documentation technique

### Notebooks
1. **01_exploration.ipynb** : Analyse des données, sparsité, distributions
2. **02_content_based_recommender.ipynb** : Implémentation CB avec PCA
3. **03_collaborative_filtering.ipynb** : SVD et ALS, gestion sparsité
4. **04_hybrid_recommender.ipynb** : Fusion et stratégie adaptative

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
  ]
}
```

## 🔮 Évolutions futures

- [ ] Intégration de Deep Learning (BERT embeddings)
- [ ] Système de feedback temps réel
- [ ] A/B testing framework
- [ ] API GraphQL
- [ ] Mise à jour incrémentale des modèles
- [ ] Support multi-langue

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

## 📝 Licence

Ce projet est réalisé dans le cadre de la formation Data Scientist d'OpenClassrooms.

---

*Dernière mise à jour : Septembre 2025*