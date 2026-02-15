# Sarvam AI MVP

This is a Minimum Viable Product (MVP) for interacting with the Sarvam AI API.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure API Key**:
    - Rename `.env.example` to `.env`
    - Add your API Key: `SARVAM_API_KEY=your_key_here`

## Usage

Run the CLI using `python3 sarvam_mvp/main.py`.

### Commands

-   **Translate**:
    ```bash
    python3 sarvam_mvp/main.py translate --text "Hello world" --target hi-IN
    ```

-   **Detect Language**:
    ```bash
    python3 sarvam_mvp/main.py detect-lang --text "Namaste"
    ```

-   **Text to Speech**:
    ```bash
    python3 sarvam_mvp/main.py tts --text "Namaste" --output output.wav
    ```

-   **Speech to Text**:
    ```bash
    python3 sarvam_mvp/main.py asr --file path/to/audio.wav
    ```

-   **Document Intelligence**:
    ```bash
    python3 sarvam_mvp/main.py document --file path/to/doc.pdf
    ```

-   **Chat**:
    ```bash
    python3 sarvam_mvp/main.py chat --prompt "Tell me a joke"
    ```

## Project Structure

-   `sarvam/`: Python package containing the SDK logic.
    -   `client.py`: Base client handling authentication and requests.
    -   `text.py`: Translation and language detection.
    -   `speech.py`: TTS and ASR.
    -   `chat.py`: Chat completion.
    -   `document.py`: Document digitization.
-   `main.py`: CLI entry point.
