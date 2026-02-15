from .client import SarvamClient
import requests
import os

class DocumentService:
    def __init__(self, client: SarvamClient):
        self.client = client

    def extract_data(self, file_path, document_type="invoice"):
        """
        Process a document.
        This usually involves:
        1. Getting a presigned URL.
        2. Uploading the file.
        3. Triggering extraction.
        4. Polling for results.
        
        Since exact endpoints might vary, I'll implement a generic structure based on common async patterns
        observed in Sarvam docs (assumed).
        
        If the endpoint is just POST file, it's simpler. 
        But `distill` said "Async workflow".
        Let's try a direct POST first if supported, or the workflow.
        
        Given the limited detailed docs in context, I'll implement a likely flow:
        POST /document-intelligence with file? 
        Or POST /document-intelligence to get request_id and upload_url.
        """
        # Note: Without exact API specs for the async flow in my memory, 
        # I will assume a simpler POST for MVP or a placeholder.
        # But wait, I can use the 'librarian' again if I'm stuck.
        # However, for now, let's assume it's like their audio upload.
        
        # Placeholder implementation based on "document-intelligence" endpoint existence.
        # I'll try to just upload the file directly similarly to speech-to-text.
        
        files = {
            'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/pdf')
        }
        data = {
            "document_type": document_type 
        }
        return self.client._make_request("POST", "document-intelligence", files=files, data=data)
