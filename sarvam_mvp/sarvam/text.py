from .client import SarvamClient

class TextService:
    def __init__(self, client: SarvamClient):
        self.client = client

    def translate(self, text, source_lang_code, target_lang_code, mode="formal", speaker_gender="male"):
        """
        Translate text.
        """
        payload = {
            "input": text,
            "source_language_code": source_lang_code,
            "target_language_code": target_lang_code,
            "mode": mode,
            "speaker_gender": speaker_gender
        }
        return self.client._make_request("POST", "translate", data=payload)

    def transliterate(self, text, source_lang_code, target_lang_code):
        """
        Transliterate text.
        """
        payload = {
            "input": text,
            "source_language_code": source_lang_code,
            "target_language_code": target_lang_code
        }
        return self.client._make_request("POST", "transliterate", data=payload)

    def detect_language(self, text):
        """
        Detect language of text.
        """
        payload = {
            "input": text
        }
        return self.client._make_request("POST", "text-lid", data=payload)
