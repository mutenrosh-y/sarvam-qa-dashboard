import os
import requests
import json
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass # Assume env vars are set if dotenv is missing

class SarvamClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        if not self.api_key:
            raise ValueError("API Key not found. Set SARVAM_API_KEY env var or pass it explicitly.")
        self.base_url = "https://api.sarvam.ai"
        self.headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }

    def _make_request(self, method, endpoint, data=None, params=None, files=None, stream=False):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Adjust headers for file uploads (remove Content-Type to let requests set boundary)
        headers = self.headers.copy()
        if files:
            headers.pop("Content-Type", None)

        response = None
        try:
            response = requests.request(
                method, 
                url, 
                headers=headers, 
                json=data if not files else None,
                data=data if files else None, # For multipart/form-data with files, data usually holds other fields
                params=params,
                files=files,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return response
                
            return response.json()
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            if response is not None:
                try:
                    print(f"Response: {response.text}")
                except:
                    pass
            raise
        except Exception as e:
            print(f"Error: {e}")
            raise
