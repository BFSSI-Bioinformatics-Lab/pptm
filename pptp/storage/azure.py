from django.conf import settings
from django.core.files.storage import Storage
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import (
    ResourceNotFoundError,
    ClientAuthenticationError,
    AzureError
)
import os
from urllib.parse import urljoin
from django.core.exceptions import SuspiciousOperation


class AzureBlobStorageError(Exception):
    pass


class AzureBlobStorage(Storage):
    def __init__(self):
        try:
            self.account_url = settings.AZURE_ACCOUNT_URL
            self.sas_token = settings.AZURE_SAS_TOKEN
            self.container = settings.AZURE_CONTAINER
            self.client = BlobServiceClient(
                account_url=self.account_url,
                credential=self.sas_token
            )
            self.container_client = self.client.get_container_client(self.container)
        except (AttributeError, ValueError) as e:
            raise AzureBlobStorageError(f"Azure storage configuration error: {str(e)}")
        except Exception as e:
            raise AzureBlobStorageError(f"Failed to initialize Azure storage: {str(e)}")

    def _save(self, name, content):
        try:
            blob_client = self.container_client.get_blob_client(name)
            content.seek(0)
            blob_client.upload_blob(content, overwrite=True)
            return name
        except ClientAuthenticationError:
            raise AzureBlobStorageError("Azure authentication token has expired")
        except AzureError as e:
            raise AzureBlobStorageError(f"Failed to save file to Azure: {str(e)}")

    def _open(self, name, mode="rb"):
        try:
            blob_client = self.container_client.get_blob_client(name)
            stream = blob_client.download_blob()
            return stream.readall()
        except ResourceNotFoundError:
            return None
        except ClientAuthenticationError:
            raise AzureBlobStorageError("Azure authentication token has expired")
        except AzureError as e:
            raise AzureBlobStorageError(f"Failed to open file from Azure: {str(e)}")

    def delete(self, name):
        try:
            blob_client = self.container_client.get_blob_client(name)
            blob_client.delete_blob()
        except ResourceNotFoundError:
            pass
        except ClientAuthenticationError:
            raise AzureBlobStorageError("Azure authentication token has expired")
        except AzureError as e:
            raise AzureBlobStorageError(f"Failed to delete file from Azure: {str(e)}")

    def exists(self, name):
        try:
            blob_client = self.container_client.get_blob_client(name)
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except ClientAuthenticationError:
            raise AzureBlobStorageError("Azure authentication token has expired")
        except AzureError as e:
            raise AzureBlobStorageError(f"Failed to check file existence in Azure: {str(e)}")

    def url(self, name):
        try:
            return self.container_client.get_blob_client(name).url
        except ClientAuthenticationError:
            raise AzureBlobStorageError("Azure authentication token has expired")
        except AzureError as e:
            raise AzureBlobStorageError(f"Failed to generate URL: {str(e)}")

    def get_valid_name(self, name):
        return name

    def get_available_name(self, name, max_length=None):
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        count = 1
        
        while self.exists(name):
            name = os.path.join(dir_name, f"{file_root}_{count}{file_ext}")
            count += 1
        return name