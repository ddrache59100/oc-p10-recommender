# 📦 Guide de Déploiement - Système de Recommandation

## 🏗️ Architecture Azure

### Ressources déployées
- **Resource Group**: `rg-p10-recommender`
- **Storage Account**: `stp10rec2025` (West Europe)
  - Container: `recommendation-models`
- **Function App**: `func-oc-p10-recommender` (France Central)
- **App Service**: `app-oc-p10-recommender-streamlit` (West Europe)
- **Application Insights**: Monitoring intégré

## 🚀 Déploiement Step-by-Step

### 1. Prérequis
- Azure CLI installé
- Azure Functions Core Tools v4
- Python 3.10
- Compte Azure avec subscription active

### 2. Configuration initiale

```bash
# Login Azure
az login

# Variables
export RG_NAME="rg-p10-recommender"
export STORAGE_NAME="stp10rec2025"
export FUNC_NAME="func-oc-p10-recommender"
export CONTAINER_NAME="recommendation-models"
```

### 3. Upload des modèles vers Blob Storage

```bash
# Récupérer la connection string
STORAGE_CONN_STR=$(az storage account show-connection-string \
  --name $STORAGE_NAME \
  --resource-group $RG_NAME \
  --query connectionString \
  --output tsv)

# Créer le container
az storage container create \
  --name $CONTAINER_NAME \
  --connection-string "$STORAGE_CONN_STR" \
  --public-access off

# Upload des modèles (depuis notebooks/models/)
az storage blob upload \
  --container-name $CONTAINER_NAME \
  --file blob_cb_pca50.pkl \
  --name models/cb_pca50.pkl \
  --connection-string "$STORAGE_CONN_STR" \
  --overwrite

az storage blob upload \
  --container-name $CONTAINER_NAME \
  --file blob_cf_svd.pkl \
  --name models/cf_svd.pkl \
  --connection-string "$STORAGE_CONN_STR" \
  --overwrite

az storage blob upload \
  --container-name $CONTAINER_NAME \
  --file blob_metadata.pkl \
  --name config/metadata.pkl \
  --connection-string "$STORAGE_CONN_STR" \
  --overwrite
```

### 4. Configuration de la Function App

```bash
# Configurer les variables d'environnement
az functionapp config appsettings set \
  --name $FUNC_NAME \
  --resource-group $RG_NAME \
  --settings \
    "AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONN_STR" \
    "BLOB_CONTAINER_NAME=$CONTAINER_NAME" \
    "FUNCTIONS_WORKER_RUNTIME=python" \
    "PYTHON_VERSION=3.10"
```

### 5. Déploiement du code

#### Option A: Avec Azure Functions Core Tools
```bash
cd azure_functions
func azure functionapp publish $FUNC_NAME --python
```

#### Option B: Avec ZIP Deploy
```bash
cd azure_functions
zip -r deploy.zip . \
  -x "*.pyc" \
  -x "__pycache__/*" \
  -x "local.settings.json" \
  -x ".venv/*"

az functionapp deployment source config-zip \
  --name $FUNC_NAME \
  --resource-group $RG_NAME \
  --src deploy.zip
```

### 6. Test du déploiement

```bash
# Test de l'API
curl -X POST "https://func-oc-p10-recommender.azurewebsites.net/api/recommend" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "history": [10, 20, 30], "n_recommendations": 5}'

# Voir les logs
az functionapp log tail \
  --name $FUNC_NAME \
  --resource-group $RG_NAME
```

## 📊 Modèles dans Blob Storage

| Fichier | Taille | Description |
|---------|---------|------------|
| `models/cb_pca50.pkl` | 69.4 MB | Embeddings PCA-50 pour Content-Based |
| `models/cf_svd.pkl` | 231.0 MB | Modèle SVD pour Collaborative Filtering |
| `config/metadata.pkl` | <1 MB | Configuration et stratégies |

## 🔧 Configuration requise

### requirements.txt
```txt
azure-functions==1.17.0
azure-storage-blob==12.19.0
numpy==1.26.4
scikit-surprise==1.1.4
```

### local.settings.json (développement local)
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=http;...",
    "BLOB_CONTAINER_NAME": "recommendation-models"
  }
}
```

## 🧪 Tests locaux avec Azurite

```bash
# Terminal 1: Démarrer Azurite
azurite-blob --silent --location ./azurite-data

# Terminal 2: Upload modèles vers Azurite
cd notebooks/models
python upload_to_azurite.py

# Terminal 3: Lancer Functions
cd azure_functions
func start

# Terminal 4: Tester
curl -X POST http://localhost:7071/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "history": [10, 20, 30], "n_recommendations": 5}'
```

## 📈 Monitoring

### Application Insights
- Traces automatiques des requêtes
- Métriques de performance
- Logs d'erreurs

### Métriques clés à surveiller
- Temps de réponse (P50, P95, P99)
- Taux d'erreur
- Utilisation mémoire
- Cache hit rate

## 🔄 Mise à jour des modèles

Pour mettre à jour les modèles sans redéployer l'API :

```bash
# Upload nouveau modèle
az storage blob upload \
  --container-name $CONTAINER_NAME \
  --file nouveau_modele.pkl \
  --name models/cb_pca50.pkl \
  --connection-string "$STORAGE_CONN_STR" \
  --overwrite

# Redémarrer la Function App pour vider le cache
az functionapp restart \
  --name $FUNC_NAME \
  --resource-group $RG_NAME
```

## ⚠️ Troubleshooting

### Erreur: scikit-surprise compilation
- Solution: Utiliser numpy 1.26.4 et scikit-surprise 1.1.4

### Erreur: Timeout au premier appel
- Normal: Chargement initial des modèles (~10s)
- Les appels suivants utilisent le cache (<1ms)

### Erreur: Connection Blob Storage
- Vérifier la connection string dans les App Settings
- Vérifier que le container existe

## 🎯 URLs de production

- **API**: https://func-oc-p10-recommender.azurewebsites.net/api/recommend
- **Streamlit**: https://app-oc-p10-recommender-streamlit.azurewebsites.net
- **Azure Portal**: https://portal.azure.com/#@/resource/subscriptions/dbc838d1-0e10-4011-90ae-899af2d1914e/resourceGroups/rg-p10-recommender

## 📝 Notes importantes

1. **Cold Start**: Le premier appel après déploiement prend ~10s (chargement des modèles)
2. **Cache**: Les modèles sont mis en cache mémoire après le premier chargement
3. **Scalabilité**: Azure Functions scale automatiquement selon la charge
4. **Coût**: ~5-10€/mois en utilisation normale

---

*Dernière mise à jour : Septembre 2025*
