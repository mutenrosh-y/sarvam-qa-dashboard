# Sarvam QA Dashboard MVP

An AI-powered Quality Assurance dashboard for call centers, built with Streamlit and Sarvam AI.

## Features
- **Upload Audio**: Process calls (MP3/WAV) using Sarvam's speech-to-text.
- **Auto-Analysis**: Get a 9-point structured analysis of every call.
- **Smart Scoring**: Upload your own scorecard (CSV) and let the AI grade the agent.
- **History**: View past analyses and scores in a searchable table.

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set API Key:**
   Create a `.env` file or export the variable:
   ```bash
   export SARVAM_API_KEY=your_key_here
   ```

3. **Run the Dashboard:**
   ```bash
   ./run.sh
   ```

## Usage
1. Open `http://localhost:8501`.
2. Upload `Sample_product_refund.mp3` (in `samples/`).
3. (Optional) Upload `sample_scorecard.csv`.
4. Click **Process Call**.

## Project Structure
- `app.py`: The Streamlit frontend.
- `sarvam_engine.py`: Core logic for STT and LLM analysis.
- `database.py`: SQLite persistence layer.
- `qa_database.db`: Local database file.
