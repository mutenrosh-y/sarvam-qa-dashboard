from .client import SarvamClient

class ChatService:
    def __init__(self, client: SarvamClient):
        self.client = client

    def completion(self, messages, model="sarvam-2b", temperature=0.1, max_tokens=500):
        """
        Get chat completion.
        messages: list of dicts [{"role": "user", "content": "..."}]
        """
        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        return self.client._make_request("POST", "chat/completions", data=payload)
