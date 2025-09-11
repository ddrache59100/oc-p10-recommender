
from azure.storage.blob import BlobServiceClient
import os

conn_str = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1"

blob_service = BlobServiceClient.from_connection_string(conn_str)

# Créer container
try:
    blob_service.create_container("recommendation-models")
    print("✅ Container créé")
except:
    print("ℹ️ Container existe déjà")

# Upload
container = blob_service.get_container_client("recommendation-models")

files = [
    ("blob_cb_pca50.pkl", "models/cb_pca50.pkl"),
    ("blob_cf_svd.pkl", "models/cf_svd.pkl"),
    ("blob_metadata.pkl", "config/metadata.pkl")
]

for local_file, blob_name in files:
    if os.path.exists(local_file):
        blob_client = container.get_blob_client(blob_name)
        with open(local_file, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        size_mb = os.path.getsize(local_file) / (1024**2)
        print(f"✅ {blob_name} uploadé ({size_mb:.1f} MB)")

print("\n✅ Modèles prêts dans Azurite!")
