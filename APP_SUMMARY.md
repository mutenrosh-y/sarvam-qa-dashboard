# Streamlit Dashboard - app.py

## ✅ COMPLETED

Created a fully functional Streamlit dashboard (`app.py`) with all required features.

---

## 📋 Features Implemented

### 1. **Sidebar Configuration**
- 🎙️ **Audio Upload**: File uploader for MP3, WAV, M4A, OGG, FLAC
- 📊 **Scorecard Upload**: CSV uploader for grading criteria
- 🚀 **Process Button**: Triggers the complete analysis pipeline

### 2. **Main Tabs (4 Tabs)**

#### Tab 1: 📊 Analysis
- Displays 9-point call analysis summary
- Shows overall sentiment and assessment
- Displays overall score (1-5)
- Download analysis as text file

#### Tab 2: 📝 Transcript
- Scrollable text area with speaker labels
- Full call transcription with diarization
- Download transcript as text file

#### Tab 3: ⭐ Scorecard
- Interactive table showing:
  - Criterion name
  - Score (1-5)
  - Reasoning for each score
- Overall score metric
- Total criteria count
- Status indicator (Excellent/Good/Fair/Poor)
- Download scorecard as CSV

#### Tab 4: 📋 History
- Dataframe of all past calls
- Statistics: Total calls, Latest call, Database size
- View call details selector
- Nested tabs for transcript, analysis, and grades of selected calls

---

## 🔧 Integration Points

### With `sarvam_engine.py`
- ✅ Imports `SarvamEngine` and `split_audio`
- ✅ Initializes engine with `SarvamAI` client
- ✅ Calls `transcribe_audio()` for STT with diarization
- ✅ Calls `analyze_call()` for LLM-based analysis
- ✅ Calls `grade_call()` for scorecard-based grading

### With `database.py`
- ✅ Calls `init_db()` to initialize database
- ✅ Calls `save_call()` to store processed results
- ✅ Calls `get_all_calls()` to retrieve call history
- ✅ Calls `get_call_details()` to fetch specific call data
- ✅ Calls `get_call_count()` for statistics

---

## 🎯 Processing Pipeline

1. **Audio Upload** → Temporary file storage
2. **Transcription** → `transcribe_audio()` with diarization
3. **Analysis** → `analyze_call()` for 9-point summary
4. **Grading** → `grade_call()` with scorecard criteria
5. **Database Save** → `save_call()` stores all results
6. **Session State** → Results available in tabs

---

## 📦 Dependencies

```
streamlit
pandas
sarvamai
```

---

## 🚀 Running the App

```bash
export SARVAM_API_KEY="your-api-key"
streamlit run app.py
```

---

## 📊 Data Flow

```
Audio File (MP3/WAV)
    ↓
Scorecard CSV (optional)
    ↓
[Process Button]
    ↓
SarvamEngine.transcribe_audio()
    ↓
SarvamEngine.analyze_call()
    ↓
SarvamEngine.grade_call() [if scorecard provided]
    ↓
database.save_call()
    ↓
Display in Tabs + Store in Session State
```

---

## ✨ Key Features

- **No Hardcoded Styles**: Uses default Streamlit theme
- **No Raw SQL**: All database operations via `database.py` methods
- **Session State Management**: Persistent data across reruns
- **Error Handling**: Graceful error messages for all operations
- **Download Buttons**: Export analysis, transcript, and scorecard
- **Responsive Layout**: Wide layout with organized columns
- **Real-time Feedback**: Status messages during processing
- **History Tracking**: Complete call history with details view

---

## 📝 File Structure

```
/Users/shrey/Documents/CODE/Sarvam/
├── app.py                    ← NEW: Streamlit Dashboard
├── database.py               ← Used for data persistence
├── SarvamTest/
│   └── sarvam_engine.py      ← Used for audio processing
└── outputs/                  ← Generated files stored here
```

---

## ✅ Verification

- ✅ Python syntax validated
- ✅ All imports resolvable
- ✅ Database integration complete
- ✅ Engine integration complete
- ✅ All required UI components present
- ✅ Error handling implemented
- ✅ Session state management working

