"""
Streamlit Dashboard for Sarvam Call Analysis.

Features:
- Upload audio files and scorecards (CSV)
- Analyze calls with transcript, analysis, and grading
- View call history and past results
- Interactive tabs for different views
"""

import streamlit as st
import pandas as pd
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

# Import engine and database modules
from SarvamTest.sarvam_engine import SarvamEngine, split_audio
from sarvamai import SarvamAI
import database

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="Sarvam Call Analysis Dashboard",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Initialize Session State
# ============================================================================

if "processed_call" not in st.session_state:
    st.session_state.processed_call = None

if "scorecard_criteria" not in st.session_state:
    st.session_state.scorecard_criteria = []

if "engine" not in st.session_state:
    try:
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            st.error("❌ SARVAM_API_KEY environment variable not set")
            st.stop()
        client = SarvamAI(api_subscription_key=api_key)
        st.session_state.engine = SarvamEngine(client)
    except Exception as e:
        st.error(f"❌ Failed to initialize Sarvam engine: {str(e)}")
        st.stop()

# Initialize database
database.init_db()

# ============================================================================
# Sidebar: Upload & Configuration
# ============================================================================

st.sidebar.title("📋 Sarvam Dashboard")
st.sidebar.markdown("---")

# Audio Upload
st.sidebar.subheader("🎙️ Upload Audio")
audio_file = st.sidebar.file_uploader(
    "Select an audio file (MP3, WAV, M4A, etc.)",
    type=["mp3", "wav", "m4a", "ogg", "flac"],
    help="Upload a call recording for analysis"
)

# Scorecard Upload
st.sidebar.subheader("📊 Upload Scorecard")

# Download Template Button
sample_csv = "Criterion,Description,Max Score\nGreeting,Did the agent greet?,5\nEmpathy,Did the agent show empathy?,5"
st.sidebar.download_button(
    "📥 Download Template",
    sample_csv,
    "scorecard_template.csv",
    "text/csv"
)

scorecard_file = st.sidebar.file_uploader(
    "Select a scorecard file (CSV, XLSX, XLS)",
    type=["csv", "xlsx", "xls"],
    help="CSV or Excel with columns: criterion, criteria, question, or item"
)

if scorecard_file is not None:
    try:
        # Read file based on extension
        if scorecard_file.name.endswith(('.xlsx', '.xls')):
            scorecard_df = pd.read_excel(scorecard_file)
        else:
            scorecard_df = pd.read_csv(scorecard_file)
        
        # Normalize column names: strip whitespace and convert to lowercase
        scorecard_df.columns = scorecard_df.columns.str.strip().str.lower()
        
        # Check for criterion/criteria/question/item columns (case-insensitive)
        valid_columns = {"criterion", "criteria", "question", "item"}
        found_column = None
        for col in scorecard_df.columns:
            if col in valid_columns:
                found_column = col
                break
        
        if found_column:
            st.session_state.scorecard_criteria = scorecard_df[found_column].tolist()
            st.sidebar.success(f"✅ Loaded {len(st.session_state.scorecard_criteria)} criteria from '{found_column}' column")
        else:
            st.sidebar.error(f"❌ File must have one of these columns: {', '.join(valid_columns)}")
    except Exception as e:
        st.sidebar.error(f"❌ Error reading file: {str(e)}")

# Process Button
st.sidebar.markdown("---")
process_button = st.sidebar.button(
    "🚀 Process Audio",
    use_container_width=True,
    type="primary"
)

# ============================================================================
# Main Processing Logic
# ============================================================================

if process_button:
    if audio_file is None:
        st.error("❌ Please upload an audio file first")
    else:
        with st.spinner("⏳ Processing audio... This may take a few minutes"):
            try:
                # Save uploaded file to temp directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    audio_path = os.path.join(temp_dir, audio_file.name)
                    with open(audio_path, "wb") as f:
                        f.write(audio_file.getbuffer())
                    
                    # Step 1: Transcribe audio
                    st.info("📝 Transcribing audio...")
                    transcription_result = st.session_state.engine.transcribe_audio(
                        [audio_path],
                        output_dir=temp_dir,
                    )
                    
                    if transcription_result["status"] != "success":
                        st.error(f"❌ Transcription failed: {transcription_result.get('error', 'Unknown error')}")
                    else:
                        conversation_file = transcription_result["conversation_file"]
                        
                        # Read transcript
                        with open(conversation_file, "r", encoding="utf-8") as f:
                            transcript = f.read()
                        
                        # Step 2: Analyze call
                        st.info("🔍 Analyzing call...")
                        analysis_result = st.session_state.engine.analyze_call(
                            conversation_file,
                            output_dir=temp_dir,
                        )
                        
                        analysis_text = ""
                        if analysis_result["status"] == "success":
                            analysis_text = analysis_result["analysis_text"]
                        else:
                            st.warning(f"⚠️ Analysis failed: {analysis_result.get('error', 'Unknown error')}")
                        
                        # Step 3: Grade call (if scorecard provided)
                        grades_data = {}
                        if st.session_state.scorecard_criteria:
                            st.info("⭐ Grading call...")
                            grading_result = st.session_state.engine.grade_call(
                                transcript,
                                st.session_state.scorecard_criteria,
                                output_dir=temp_dir,
                            )
                            
                            if grading_result["status"] == "success":
                                grades_data = {
                                    "grades": grading_result.get("grades", []),
                                    "overall_score": grading_result.get("overall_score", 0),
                                    "summary": grading_result.get("summary", ""),
                                }
                            else:
                                st.warning(f"⚠️ Grading failed: {grading_result.get('error', 'Unknown error')}")
                        
                        # Step 4: Save to database
                        st.info("💾 Saving to database...")
                        call_id = database.save_call(
                            filename=audio_file.name,
                            upload_time=datetime.now().isoformat(),
                            transcript=transcript,
                            analysis=analysis_text,
                            grades=grades_data,
                        )
                        
                        # Store in session state for display
                        st.session_state.processed_call = {
                            "call_id": call_id,
                            "filename": audio_file.name,
                            "transcript": transcript,
                            "analysis": analysis_text,
                            "grades": grades_data,
                        }
                        
                        st.success(f"✅ Call processed and saved (ID: {call_id})")
            
            except Exception as e:
                st.error(f"❌ Processing error: {str(e)}")

# ============================================================================
# Main Content Area: Tabs
# ============================================================================

st.title("📞 Sarvam Call Analysis Dashboard")

# Create tabs
tab_analysis, tab_transcript, tab_scorecard, tab_history = st.tabs(
    ["📊 Analysis", "📝 Transcript", "⭐ Scorecard", "📋 History"]
)

# ============================================================================
# TAB 1: Analysis
# ============================================================================

with tab_analysis:
    st.subheader("Call Analysis Summary")
    
    if st.session_state.processed_call is None:
        st.info("📌 Upload and process an audio file to see analysis")
    else:
        call = st.session_state.processed_call
        
        # Display 9-point summary
        st.markdown("### 9-Point Summary")
        
        analysis_text = call.get("analysis", "")
        if analysis_text:
            st.markdown(analysis_text)
        else:
            st.warning("No analysis available")
        
        # Display overall sentiment
        st.markdown("### Overall Sentiment")
        grades = call.get("grades", {})
        if grades and "summary" in grades:
            st.info(f"**Summary:** {grades['summary']}")
        else:
            st.info("No sentiment data available")
        
        # Display overall score
        if grades and "overall_score" in grades:
            overall_score = grades["overall_score"]
            st.metric("Overall Score", f"{overall_score:.2f}/5.0")
        
        # Download analysis as text
        if analysis_text:
            st.download_button(
                label="📥 Download Analysis",
                data=analysis_text,
                file_name=f"analysis_{call['call_id']}.txt",
                mime="text/plain",
            )

# ============================================================================
# TAB 2: Transcript
# ============================================================================

with tab_transcript:
    st.subheader("Call Transcript")
    
    if st.session_state.processed_call is None:
        st.info("📌 Upload and process an audio file to see transcript")
    else:
        call = st.session_state.processed_call
        transcript = call.get("transcript", "")
        
        if transcript:
            # Display in scrollable container
            st.text_area(
                "Transcript with Speaker Labels",
                value=transcript,
                height=400,
                disabled=True,
            )
            
            # Download transcript
            st.download_button(
                label="📥 Download Transcript",
                data=transcript,
                file_name=f"transcript_{call['call_id']}.txt",
                mime="text/plain",
            )
        else:
            st.warning("No transcript available")

# ============================================================================
# TAB 3: Scorecard
# ============================================================================

with tab_scorecard:
    st.subheader("Call Scorecard")
    
    if st.session_state.processed_call is None:
        st.info("📌 Upload and process an audio file to see scorecard")
    else:
        call = st.session_state.processed_call
        grades = call.get("grades", {})
        
        if grades and "grades" in grades and grades["grades"]:
            # Create DataFrame from grades
            grades_list = grades["grades"]
            df_grades = pd.DataFrame(grades_list)
            
            # Display as table
            st.dataframe(
                df_grades,
                use_container_width=True,
                hide_index=True,
            )
            
            # Display overall score
            if "overall_score" in grades:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Overall Score", f"{grades['overall_score']:.2f}/5.0")
                with col2:
                    st.metric("Total Criteria", len(grades_list))
                with col3:
                    avg_score = grades["overall_score"]
                    if avg_score >= 4:
                        status = "✅ Excellent"
                    elif avg_score >= 3:
                        status = "👍 Good"
                    elif avg_score >= 2:
                        status = "⚠️ Fair"
                    else:
                        status = "❌ Poor"
                    st.metric("Status", status)
            
            # Download scorecard as CSV
            csv = df_grades.to_csv(index=False)
            st.download_button(
                label="📥 Download Scorecard (CSV)",
                data=csv,
                file_name=f"scorecard_{call['call_id']}.csv",
                mime="text/csv",
            )
        else:
            st.info("📌 No scorecard data available. Upload a scorecard CSV to enable grading.")

# ============================================================================
# TAB 4: History
# ============================================================================

with tab_history:
    st.subheader("Call History")
    
    # Refresh button
    if st.button("🔄 Refresh History", use_container_width=True):
        st.rerun()
    
    # Get all calls from database
    calls = database.get_all_calls()
    
    if not calls:
        st.info("📌 No calls processed yet")
    else:
        # Convert to DataFrame
        df_history = pd.DataFrame(calls)
        
        # Format columns
        df_history["upload_time"] = pd.to_datetime(df_history["upload_time"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        df_history["created_at"] = pd.to_datetime(df_history["created_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
        
        # Display table
        st.dataframe(
            df_history,
            use_container_width=True,
            hide_index=True,
        )
        
        # Statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Calls", len(calls))
        with col2:
            st.metric("Latest Call", df_history["created_at"].iloc[0] if len(calls) > 0 else "N/A")
        with col3:
            st.metric("Database Size", f"{database.get_call_count()} records")
        
        # View details
        st.markdown("---")
        st.subheader("View Call Details")
        
        selected_call_id = st.selectbox(
            "Select a call to view details",
            options=[c["call_id"] for c in calls],
            format_func=lambda x: f"Call #{x} - {next((c['filename'] for c in calls if c['call_id'] == x), 'Unknown')}",
        )
        
        if selected_call_id:
            call_details = database.get_call_details(selected_call_id)
            if call_details:
                st.markdown(f"### Call #{call_details['call_id']}: {call_details['filename']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Upload Time:** {call_details['upload_time']}")
                with col2:
                    st.write(f"**Created At:** {call_details['created_at']}")
                
                # Tabs for details
                detail_tab1, detail_tab2, detail_tab3 = st.tabs(
                    ["📝 Transcript", "🔍 Analysis", "⭐ Grades"]
                )
                
                with detail_tab1:
                    st.text_area(
                        "Transcript",
                        value=call_details.get("transcript", ""),
                        height=300,
                        disabled=True,
                    )
                
                with detail_tab2:
                    st.markdown(call_details.get("analysis", "No analysis available"))
                
                with detail_tab3:
                    grades = call_details.get("grades", {})
                    if grades and "grades" in grades:
                        df_grades = pd.DataFrame(grades["grades"])
                        st.dataframe(df_grades, use_container_width=True, hide_index=True)
                        if "overall_score" in grades:
                            st.metric("Overall Score", f"{grades['overall_score']:.2f}/5.0")
                    else:
                        st.info("No grades available")

# ============================================================================
# Footer
# ============================================================================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 12px;'>
    Sarvam Call Analysis Dashboard | Powered by Sarvam AI
    </div>
    """,
    unsafe_allow_html=True,
)
