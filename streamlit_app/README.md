# 🎯 My Content Recommender - Interface Streamlit

Application web pour démontrer le système de recommandation Content-Based développé dans le cadre du Projet 10 OpenClassrooms.

## 🚀 Démarrage rapide

### Installation

```bash
# Installer les dépendances
pip install -r requirements.txt
```

### Lancement local

```bash
# Terminal 1 - Lancer l'API Azure Functions
cd ../azure_functions
func start

# Terminal 2 - Lancer Streamlit
cd streamlit_app
streamlit run app.py
```

### Accès

**Développement local :**
- Application : http://localhost:8501
- API : http://localhost:7071

**Production Azure :**
- Application : https://app-oc-p10-recommender-streamlit.azurewebsites.net
- API : https://func-oc-p10-recommender.azurewebsites.net

## 📊 Fonctionnalités

### Interface
- Sélection utilisateur (ID ou aléatoire)
- Visualisation de l'historique de clics
- Affichage des recommandations avec scores
- Métriques de performance en temps réel

### Modes de données
- **Sample** : 707 utilisateurs, 323 articles (démo rapide)
- **Complet** : 322k utilisateurs, 364k articles (dataset Globo.com)

### Profils utilisateurs
- 🆕 **Cold Start** (≤5 clics) : Articles populaires
- 📊 **Modéré** (6-15 clics) : Content-Based
- 🔥 **Actif** (>15 clics) : Content-Based optimisé

## 🏗️ Architecture

```
┌─────────────────┐          ┌──────────────────┐
│  Streamlit App  │  POST    │ Azure Functions  │
│                 │────────▶│      API         │
│ • Charge clicks │          │ • Calcul profil  │
│ • Envoie history│          │ • Similarité     │
│ • Affiche reco  │◀────────│ • Top-N articles │
└─────────────────┘  JSON    └──────────────────┘
        │                            │
        ▼                            ▼
  ┌──────────┐                ┌───────────┐
  │ clicks   │                │ PCA-50    │
  │ .csv     │                │ Embeddings│
  └──────────┘                └───────────┘
```

## 📁 Structure

```
streamlit_app/
├── app.py                 # Application principale (14KB)
├── data/
│   ├── clicks.parquet    # Dataset complet (50MB)
│   └── clicks_sample.csv # Sample pour démo (131KB)
├── requirements.txt       # Dépendances Python
└── README.md             # Ce fichier
```

## ⚙️ Configuration

Dans `app.py` :
```python
# API endpoint (local par défaut, production si variable d'environnement définie)
API_URL = os.getenv('AZURE_FUNCTION_URL', 'http://localhost:7071')

# Data mode
USE_SAMPLE = True  # True pour démo, False pour dataset complet
```

## 📈 Métriques affichées

| Métrique | Description | Valeur typique |
|----------|-------------|----------------|
| **Temps API** | Calcul recommandations | ~46ms |
| **Temps total** | Round-trip complet | ~240ms |
| **Score similarité** | Cosinus similarity | 0.65-0.75 |
| **Profil** | Cold/Moderate/Active | Selon historique |

## 🧪 Test de connexion

```bash
# Test API locale
curl http://localhost:7071/api/recommend/1

# Test API production
curl https://func-oc-p10-recommender.azurewebsites.net/api/recommend/1
```

## 🐛 Résolution de problèmes

| Problème | Solution |
|----------|----------|
| API déconnectée (local) | Vérifier que Azure Functions est lancé sur le port 7071 |
| API déconnectée (prod) | Vérifier le status sur Azure Portal |
| Fichier non trouvé | Vérifier que `data/clicks_sample.csv` existe |
| Port utilisé | Changer avec `streamlit run app.py --server.port 8502` |

## 🚀 Déploiement Azure

Le système est déployé et accessible en production :

| Service | URL | Status |
|---------|-----|--------|
| **Streamlit App** | https://app-oc-p10-recommender-streamlit.azurewebsites.net | ✅ Running |
| **API Functions** | https://func-oc-p10-recommender.azurewebsites.net | ✅ Running |

Pour déployer une nouvelle version :
```bash
# API
cd azure_functions
func azure functionapp publish func-oc-p10-recommender

# Streamlit
cd streamlit_app
az webapp up --name app-oc-p10-recommender-streamlit
```

## 📝 Notes techniques

- **Modèle** : Embeddings PCA-50 (94.3% variance conservée)
- **Algorithme** : Similarité cosinus entre profil utilisateur et articles
- **Cache** : Optimisation des requêtes répétées
- **Couverture** : 100% des utilisateurs reçoivent des recommandations
- **Taille modèle** : 71 MB (optimisé pour Azure Functions)

---

**Auteur** : Didier DRACHE  
**Formation** : Data & AI Engineer - OpenClassrooms  
**Projet** : 10 - Système de Recommandation  
**Date** : Septembre 2025
