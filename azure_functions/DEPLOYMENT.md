# 📚 Guide de déploiement Azure Functions

## 🏗️ Structure du projet

```
azure_functions/
├── models/
│   └── hybrid_azure.pkl           # Modèle Content-Based PCA-50 (71 MB)
├── shared/
│   └── recommendation_api.py      # API de recommandation
├── RecommendationFunction/
│   ├── __init__.py                # Point d'entrée Azure
│   └── function.json              # Configuration de la fonction
├── host.json                      # Configuration globale
├── local.settings.json            # Settings locaux (ignoré par git)
├── requirements.txt               # Dépendances Python
└── test_azure_local.py           # Tests unitaires
```

## 🚀 Test local

```bash
# 1. Installer Azure Functions Core Tools
# https://docs.microsoft.com/azure/azure-functions/functions-run-local

# 2. Lancer la fonction localement
cd azure_functions
func start

# 3. Tester l'API
curl -X POST http://localhost:7071/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "user_history": [45678, 91234, 67890],
    "n_recommendations": 5
  }'

# 4. Ou utiliser le script de test
python test_azure_local.py
```

## ☁️ Déploiement Azure

### Prérequis
- Azure CLI installé
- Compte Azure avec crédits disponibles
- Python 3.10

### Déployer la fonction

```bash
# 1. Se connecter à Azure
az login

# 2. Créer les ressources si nécessaire
az group create --name rg-oc-p10 --location westeurope
az storage account create --name stocp10recommender --resource-group rg-oc-p10
az functionapp create \
  --name func-oc-p10-recommender \
  --resource-group rg-oc-p10 \
  --storage-account stocp10recommender \
  --consumption-plan-location westeurope \
  --runtime python \
  --runtime-version 3.10 \
  --functions-version 4

# 3. Déployer le code
func azure functionapp publish func-oc-p10-recommender --python

# 4. Vérifier le déploiement
curl https://func-oc-p10-recommender.azurewebsites.net/api/recommend/1
```

## 📊 Configuration

### local.settings.json (pour dev local)
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "MODEL_PATH": "models/hybrid_azure.pkl"
  }
}
```

### Variables d'environnement Azure
```bash
# Configurer les settings en production
az functionapp config appsettings set \
  --name func-oc-p10-recommender \
  --resource-group rg-oc-p10 \
  --settings MODEL_PATH=models/hybrid_azure.pkl
```

## 🎯 Endpoints API

### POST /api/recommend
**Request:**
```json
{
  "user_id": 123,
  "user_history": [235840, 96663, 59758],
  "n_recommendations": 5
}
```

**Response:**
```json
{
  "status": "success",
  "user_id": 123,
  "n_history": 3,
  "recommendations": [
    {"rank": 1, "article_id": 246991, "score": 0.690},
    {"rank": 2, "article_id": 233727, "score": 0.683}
  ],
  "inference_time_ms": 46.0,
  "from_cache": false
}
```

## ⚙️ Architecture technique

### Modèle déployé
- **Type**: Content-Based avec embeddings PCA
- **Dimensions**: 364,047 articles × 50 dimensions
- **Taille**: 71 MB
- **Variance conservée**: 94.3%
- **Algorithme**: Similarité cosinus

### Performance
- **Temps de calcul**: ~46ms sans cache
- **Avec cache**: <5ms
- **Mémoire requise**: ~500 MB runtime
- **Cold start Azure**: 2-3 secondes

## 🧪 Tests

```bash
# Tests unitaires locaux
python test_azure_local.py

# Test de charge
hey -n 100 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"user_history":[1,2,3],"n_recommendations":5}' \
  https://func-oc-p10-recommender.azurewebsites.net/api/recommend
```

## 📈 Monitoring

```bash
# Voir les logs en temps réel
func azure functionapp logstream func-oc-p10-recommender

# Métriques dans Azure Portal
az monitor metrics list \
  --resource func-oc-p10-recommender \
  --resource-group rg-oc-p10 \
  --resource-type Microsoft.Web/sites
```

## 🐛 Troubleshooting

| Problème | Solution |
|----------|----------|
| Module not found | Vérifier requirements.txt et redéployer |
| Timeout (>30s) | Optimiser le code ou passer au plan Premium |
| Out of memory | Réduire la taille du modèle ou augmenter le plan |
| Cold start lent | Utiliser le plan Premium avec Always On |

## 📦 Dépendances

Fichier `requirements.txt`:
```
azure-functions
numpy==1.24.3
pandas==2.0.3
scikit-learn==1.3.0
```

## 🔒 Sécurité

- Le modèle est inclus dans le package de déploiement
- Pas de secrets dans le code (utiliser Key Vault si nécessaire)
- CORS configuré pour accepter uniquement l'app Streamlit
- Authentification possible via API keys ou Azure AD

## 💰 Coûts estimés

| Plan | Requêtes/mois | Coût estimé |
|------|---------------|-------------|
| Consumption | < 1M | Gratuit |
| Consumption | 10M | ~20€ |
| Premium | Illimité | ~150€/mois |

## 📝 Notes importantes

- ✅ Modèle Content-Based uniquement (pas de Collaborative Filtering)
- ✅ Compatible Azure Functions Python 3.10
- ✅ Gestion du cache pour optimiser les performances
- ✅ 100% de couverture utilisateurs
- ⚠️ Taille du modèle: 71 MB (attention aux limites du plan Consumption)

## 🔗 URLs de production

- **API**: https://func-oc-p10-recommender.azurewebsites.net
- **Documentation API**: https://func-oc-p10-recommender.azurewebsites.net/api/swagger
- **Azure Portal**: https://portal.azure.com

---

**Dernière mise à jour**: Septembre 2025  
**Auteur**: Didier DRACHE  
**Contact**: Support via Azure Portal
