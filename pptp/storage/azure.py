from django.conf import settings
from django.core.files.storage import Storage
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
import os
from urllib.parse import urljoin


class AzureBlobStorage(Storage):
    def __init__(self):
        self.account_url = settings.AZURE_ACCOUNT_URL
        self.sas_token = settings.AZURE_SAS_TOKEN
        self.container = settings.AZURE_CONTAINER
        
        self.client = BlobServiceClient(
            account_url=self.account_url,
            credential=self.sas_token
        )
        self.container_client = self.client.get_container_client(self.container)

    def _save(self, name, content):
        blob_client = self.container_client.get_blob_client(name)
        content.seek(0)
        blob_client.upload_blob(content, overwrite=True)
        return name

    def _open(self, name, mode="rb"):
        try:
            blob_client = self.container_client.get_blob_client(name)
            stream = blob_client.download_blob()
            return stream.readall()
        except ResourceNotFoundError:
            return None

    def delete(self, name):
        try:
            blob_client = self.container_client.get_blob_client(name)
            blob_client.delete_blob()
        except ResourceNotFoundError:
            pass

    def exists(self, name):
        try:
            blob_client = self.container_client.get_blob_client(name)
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    def url(self, name):
        #if settings.AZURE_CUSTOM_DOMAIN:
        #   return urljoin(settings.AZURE_CUSTOM_DOMAIN, name)
        return self.container_client.get_blob_client(name).url

    def get_valid_name(self, name):
        return name

    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            dir_name, file_name = os.path.split(name)
            file_root, file_ext = os.path.splitext(file_name)
            count = 1
            while self.exists(name):
                name = os.path.join(
                    dir_name, f"{file_root}_{count}{file_ext}"
                )
                count += 1
        return name