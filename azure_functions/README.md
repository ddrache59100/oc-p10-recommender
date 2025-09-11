# API de Recommandation Hybride

## Architecture
- Azure Functions (Serverless)
- Azure Blob Storage pour les modèles
- Système hybride CB + CF adaptatif

## Test local
1. Démarrer Azurite : `azurite-blob --silent`
2. Upload modèles : `python notebooks/models/upload_to_azurite.py`
3. Lancer API : `func start`

## Endpoints
POST /api/recommend