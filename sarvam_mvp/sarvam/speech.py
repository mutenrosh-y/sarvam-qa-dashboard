from .client import SarvamClient
import os

class SpeechService:
    def __init__(self, client: SarvamClient):
        self.client = client

    def text_to_speech(self, text, target_language_code="hi-IN", speaker="meera", model="bulbul:v1"):
        """
        Convert text to speech.
        """
        payload = {
            "inputs": [text],
            "target_language_code": target_language_code,
            "speaker": speaker,
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 8000,
            "enable_preprocessing": True,
            "model": model
        }
        return self.client._make_request("POST", "text-to-speech", data=payload)

    def speech_to_text(self, audio_file_path, language_code=None, model="saaras:v1"):
        """
        Convert speech to text.
        """
        # Multipart form data
        files = {
            'file': (os.path.basename(audio_file_path), open(audio_file_path, 'rb'), 'audio/wav')
        }
        # data payload
        data = {
            'model': model
        }
        if language_code:
            data['language_code'] = language_code

        return self.client._make_request("POST", "speech-to-text", files=files, data=data)

    def speech_to_text_translate(self, audio_file_path, model="saarika:v1"):
        """
        Convert speech to text and translate.
        """
        files = {
            'file': (os.path.basename(audio_file_path), open(audio_file_path, 'rb'), 'audio/wav')
        }
        data = {
            'model': model
        }
        return self.client._make_request("POST", "speech-to-text-translate", files=files, data=data)
