import click
import os
import json
from sarvam.client import SarvamClient
from sarvam.text import TextService
from sarvam.speech import SpeechService
from sarvam.chat import ChatService
from sarvam.document import DocumentService

# Helper to print formatted JSON
def print_json(data):
    click.echo(json.dumps(data, indent=2, ensure_ascii=False))

@click.group()
def cli():
    """Sarvam AI MVP CLI"""
    pass

@cli.command()
@click.option('--text', prompt='Text to translate', help='Text to translate')
@click.option('--source', default='en-IN', help='Source language code (e.g., en-IN)')
@click.option('--target', default='hi-IN', help='Target language code (e.g., hi-IN)')
def translate(text, source, target):
    """Translate text"""
    client = SarvamClient()
    service = TextService(client)
    try:
        result = service.translate(text, source, target)
        print_json(result)
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--text', prompt='Text to detect', help='Text to detect language')
def detect_lang(text):
    """Detect Language"""
    client = SarvamClient()
    service = TextService(client)
    try:
        result = service.detect_language(text)
        print_json(result)
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--text', prompt='Text to speak', help='Text to convert to speech')
@click.option('--lang', default='hi-IN', help='Language code (e.g., hi-IN)')
@click.option('--output', default='output.wav', help='Output file path')
def tts(text, lang, output):
    """Text to Speech"""
    client = SarvamClient()
    service = SpeechService(client)
    try:
        # Note: API returns base64 encoded audio in JSON field 'audios' (list) usually
        result = service.text_to_speech(text, target_language_code=lang)
        
        # Check if result is a list of audios or direct content
        # Common Sarvam pattern: {"audios": ["base64_string", ...]}
        if isinstance(result, dict) and "audios" in result:
            import base64
            audio_data = base64.b64decode(result["audios"][0])
            with open(output, "wb") as f:
                f.write(audio_data)
            click.echo(f"Audio saved to {output}")
        else:
            print_json(result)
            click.echo("Unexpected response format. Check output above.")
            
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--file', prompt='Audio file path', help='Path to audio file')
def asr(file):
    """Speech to Text"""
    client = SarvamClient()
    service = SpeechService(client)
    try:
        result = service.speech_to_text(file)
        print_json(result)
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--file', prompt='Document file path', help='Path to document')
@click.option('--type', default='invoice', help='Document type')
def document(file, type):
    """Document Intelligence"""
    client = SarvamClient()
    service = DocumentService(client)
    try:
        result = service.start_digitization_job(file, document_type=type)
        print_json(result)
    except Exception as e:
        click.echo(f"Error: {e}")

@cli.command()
@click.option('--prompt', prompt='Prompt', help='User prompt')
def chat(prompt):
    """Chat Completion"""
    client = SarvamClient()
    service = ChatService(client)
    messages = [{"role": "user", "content": prompt}]
    try:
        result = service.completion(messages)
        print_json(result)
    except Exception as e:
        click.echo(f"Error: {e}")

if __name__ == '__main__':
    cli()
