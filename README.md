# Sarvam QA Dashboard 🎧

> **AI-powered Quality Assurance for Call Centers**  
> *Built with [Sarvam AI](https://www.sarvam.ai/) & [Streamlit](https://streamlit.io/)*

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-red)
![Sarvam AI](https://img.shields.io/badge/Powered%20by-Sarvam%20AI-orange)

## 📋 Overview

The **Sarvam QA Dashboard** is a specialized tool designed to audit customer service calls automatically. By leveraging Sarvam AI's speech-to-text and LLM capabilities, it provides:
- **Automated Transcription**: High-accuracy speech recognition for Indian languages and English.
- **9-Point Call Analysis**: Structured breakdown of every interaction (Problem, Resolution, Sentiment, etc.).
- **Smart Scoring (LLM-as-a-Judge)**: Auto-grade agents based on your custom Scorecard criteria.
- **Historical Tracking**: Searchable database of all past audits.

---

## 🚀 Features

### 1. 🎙️ Audio Processing
- **Upload**: Supports `.mp3`, `.wav`, `.m4a`.
- **Diarization**: Distinguishes between Agent and Customer.
- **Playback**: Integrated audio player with synchronized transcript view.

### 2. 📊 Intelligent Analysis
Auto-generated insights including:
- **Summary**: Concise 2-3 word tag.
- **Customer Sentiment**: (Positive/Neutral/Negative).
- **Key Issues**: What went wrong?
- **Resolution Status**: Was the problem solved?

### 3. 📝 Custom Scorecards
Upload a CSV to define your own QA criteria. The AI acts as an unbiased auditor.
**Format:**
```csv
Category,Criteria,Description,Max Score
Greeting,Professionalism,Did the agent introduce themselves?,5
Resolution,Accuracy,Was the correct solution provided?,10
```

---

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- [Sarvam AI API Key](https://dashboard.sarvam.ai/)

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/sarvam-qa-dashboard.git
   cd sarvam-qa-dashboard
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Create a `.env` file in the root directory:
   ```bash
   SARVAM_API_KEY=your_api_key_here
   ```

4. **Run the Dashboard:**
   ```bash
   streamlit run app.py
   ```
   Access at `http://localhost:8501`.

---

## ☁️ Deployment

### Option 1: Streamlit Community Cloud (Recommended)
The easiest way to host this app for free.

1. Push this code to **GitHub**.
2. Go to [share.streamlit.io](https://share.streamlit.io/).
3. Connect your GitHub account and select this repository.
4. In **Advanced Settings**, add your secret:
   - Key: `SARVAM_API_KEY`
   - Value: `sk_...`
5. Click **Deploy**! 🎈

### Option 2: Docker / Vercel
*Note: Streamlit requires a persistent server. For Vercel, you may need a containerized approach.*

**Dockerfile:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## 📂 Project Structure

| File | Description |
|------|-------------|
| `app.py` | Main Streamlit application frontend. |
| `sarvam_engine.py` | Core library interacting with Sarvam API. |
| `database.py` | SQLite database manager for history. |
| `samples/` | Sample audio files for testing. |
| `qa_database.db` | Local database (created on first run). |

---

## 🛡️ License

MIT License. See [LICENSE](LICENSE) for details.
