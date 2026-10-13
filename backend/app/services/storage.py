import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")

class StorageService:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase credentials not fully configured.")
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.bucket_name = "medical-documents"
        
        # Ensure bucket exists
        try:
            buckets = self.client.storage.list_buckets()
            if not any(b.name == self.bucket_name for b in buckets):
                self.client.storage.create_bucket(self.bucket_name, {"public": False})
                print(f"Created Supabase bucket: {self.bucket_name}")
        except Exception as e:
            print(f"Failed to check/create bucket: {e}")

    def upload_file(self, file_path: str, file_bytes: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Uploads encrypted file bytes to Supabase Storage.
        """
        response = self.client.storage.from_(self.bucket_name).upload(
            path=file_path,
            file=file_bytes,
            file_options={"content-type": content_type}
        )
        
        # supabase-py can sometimes return a dict with an error or a Response object on failure
        if hasattr(response, "error") and response.error:
            raise Exception(f"Supabase upload failed: {response.error}")
        if isinstance(response, dict) and response.get("error"):
            raise Exception(f"Supabase upload failed: {response.get('error')}")
            
        return file_path

    def download_file(self, file_path: str) -> bytes:
        """
        Downloads encrypted file bytes from Supabase Storage.
        """
        return self.client.storage.from_(self.bucket_name).download(file_path)

storage_service = StorageService()
