"""
Sarvam Engine - Core logic for Audio processing, STT, and LLM Analysis.

Refactored from sarvam_analytics.py for library use.
"""

import json
import os
import tempfile
import typing
import hashlib
import textwrap
from datetime import datetime

# Initialize static_ffmpeg BEFORE importing pydub so pydub finds ffmpeg/ffprobe
import static_ffmpeg
static_ffmpeg.add_paths()

from pydub import AudioSegment
from sarvamai import SarvamAI


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

ANALYSIS_PROMPT_TEMPLATE = """
Analyze this call transcription thoroughly from start to finish.

TRANSCRIPTION:
{transcription}

Please answer the following:

1. Identify which speaker is the **customer** and which one is the **agent**.
2. Determine if the customer is a **new/potential customer** or an **existing customer**.
3. What **problem, query, or doubt** did the customer raise at the beginning?
4. What **services/products** was the customer inquiring about or facing issues with?
5. How did the agent respond to and resolve the issue throughout the call?
6. Was the **customer satisfied** at the end of the call?
7. Did the customer express any **emotions or sentiments** (positive, negative, or neutral)?
8. Were there any mentions of **competitors**, or any opportunities for **upselling or cross-selling**?
9. Summarize the **resolution** and whether it was successful.

Provide your answer in a clear, structured format with section headings and bullet points.
"""

SUMMARY_PROMPT_TEMPLATE = """
Based on this call analysis, summarize each of the following in 2–3 words:

{analysis_text}

1. Customer & Agent
2. Customer Type
3. Main Issue
4. Service Discussed
5. Agent's Response
6. Customer Satisfaction
7. Sentiment
8. Competitor or Upsell
9. Resolution
"""

GRADING_PROMPT_TEMPLATE = """
You are a QA Specialist grading a customer service call based on a specific scorecard.

TRANSCRIPTION:
{transcription}

SCORECARD CRITERIA:
{criteria_text}

For EACH criterion, provide:
1. Score (1-5, where 5 is best)
2. Reasoning (Cite specific evidence from the transcript)

Return the result as a valid JSON object with this structure:
{{
  "grades": [
    {{
      "criteria": "Greeting",
      "score": 5,
      "reasoning": "Agent explicitly mentioned their name and company."
    }},
    ...
  ],
  "overall_score": 4.5,
  "summary": "Brief summary of performance"
}}
"""


# ---------------------------------------------------------------------------
# Audio utilities
# ---------------------------------------------------------------------------

def split_audio(
    audio_path: str,
    chunk_duration_ms: int = 60 * 60 * 1000,  # 1 hour
    output_dir: typing.Optional[str] = None,
) -> typing.List[str]:
    """Split an audio file into chunks of *chunk_duration_ms* milliseconds."""
    audio = AudioSegment.from_file(audio_path)

    if len(audio) <= chunk_duration_ms:
        return [audio_path]

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="sarvam_chunks_")
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    ext = os.path.splitext(audio_path)[1] or ".wav"

    chunks: typing.List[str] = []
    for i, start in enumerate(range(0, len(audio), chunk_duration_ms)):
        chunk = audio[start : start + chunk_duration_ms]
        chunk_path = os.path.join(output_dir, f"{base_name}_chunk{i:03d}{ext}")
        chunk.export(chunk_path)
        chunks.append(chunk_path)

    return chunks


# ---------------------------------------------------------------------------
# CallAnalytics Engine
# ---------------------------------------------------------------------------

class CallAnalytics:
    """Orchestrates Sarvam STT Batch API with diarization and parses results."""

    def __init__(self, client: SarvamAI) -> None:
        self.client = client

    def process_audio_files(
        self,
        audio_paths: typing.List[str],
        output_dir: str = "outputs",
        model: str = "saaras:v3",
        num_speakers: typing.Optional[int] = None,
    ) -> typing.Dict[str, str]:
        """Submit audio files to Sarvam STT Batch API and return parsed results."""
        os.makedirs(output_dir, exist_ok=True)

        # 1. Split long audio files if necessary
        all_paths: typing.List[str] = []
        for path in audio_paths:
            all_paths.extend(split_audio(path))

        # Resolve to absolute paths for the upload step
        all_paths = [os.path.abspath(p) for p in all_paths]

        print(f"[CallAnalytics] Processing {len(all_paths)} file(s)...")

        # 2. Create STT Translate batch job
        job = self.client.speech_to_text_translate_job.create_job(
            model=model,
            with_diarization=True,
            num_speakers=num_speakers,
        )
        print(f"[CallAnalytics] Job created: {job.job_id}")

        # 3. Upload files
        job.upload_files(file_paths=all_paths)
        print("[CallAnalytics] Files uploaded.")

        # 4. Start the job
        job.start()
        print("[CallAnalytics] Job started. Waiting for completion...")

        # 5. Wait for completion (poll every 5s, timeout 600s)
        status = job.wait_until_complete(poll_interval=5, timeout=600)
        print(f"[CallAnalytics] Job finished with state: {status.job_state}")

        if status.job_state.lower() == "failed":
            raise RuntimeError(
                f"STT batch job {job.job_id} failed. Check Sarvam dashboard."
            )

        # 6. Download outputs
        raw_output_dir = os.path.join(output_dir, "raw")
        job.download_outputs(output_dir=raw_output_dir)
        print(f"[CallAnalytics] Outputs downloaded to {raw_output_dir}")

        # 7. Parse transcriptions
        result = self._parse_transcriptions(raw_output_dir, output_dir)
        return result

    def _parse_transcriptions(
        self,
        raw_output_dir: str,
        output_dir: str,
    ) -> typing.Dict[str, str]:
        """Parse downloaded STT JSON files into conversation + timing outputs."""
        all_entries: typing.List[typing.Dict[str, typing.Any]] = []

        # Collect diarized entries from every result file
        for fname in sorted(os.listdir(raw_output_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(raw_output_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            diarized = data.get("diarized_transcript", {})
            entries = diarized.get("entries", [])
            all_entries.extend(entries)

            # Fallback
            if not entries and "transcript" in data:
                all_entries.append({
                    "speaker_id": "SPEAKER_00",
                    "transcript": data["transcript"],
                    "start_time_seconds": 0.0,
                    "end_time_seconds": 0.0,
                })

        conversation_lines: typing.List[str] = []
        speaker_times: typing.Dict[str, float] = {}

        for entry in all_entries:
            speaker = entry.get("speaker_id", "UNKNOWN")
            text = entry.get("transcript", "").strip()
            start = entry.get("start_time_seconds", 0.0)
            end = entry.get("end_time_seconds", 0.0)
            duration = max(end - start, 0.0)

            conversation_lines.append(f"{speaker}: {text}")
            speaker_times[speaker] = speaker_times.get(speaker, 0.0) + duration

        conversation_file = os.path.join(output_dir, "_conversation.txt")
        with open(conversation_file, "w", encoding="utf-8") as f:
            f.write("\n".join(conversation_lines))
            f.write("\n")

        timing_file = os.path.join(output_dir, "_timing.json")
        with open(timing_file, "w", encoding="utf-8") as f:
            json.dump(speaker_times, f, indent=2, ensure_ascii=False)
            f.write("\n")

        return {
            "conversation_file": conversation_file,
            "timing_file": timing_file,
            "raw_output_dir": raw_output_dir,
        }

    def analyze_transcription(
        self,
        conversation_file: str,
        output_dir: str,
    ) -> typing.Optional[str]:
        """Analyze a transcription using LLM to extract structured insights."""
        base_name = os.path.basename(conversation_file).replace("_conversation.txt", "")
        print(f"[CallAnalytics] Analyzing transcription for {base_name}...")

        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                transcription = f.read()

            if not transcription.strip():
                return None

            prompt_content = ANALYSIS_PROMPT_TEMPLATE.format(transcription=transcription)
            messages = [
                {
                    "role": "system",
                    "content": "You are a call analytics expert. Provide structured insights."
                },
                {"role": "user", "content": textwrap.dedent(prompt_content)},
            ]

            response = self.client.chat.completions(
                messages=messages,
                temperature=0.0,
            )

            analysis_text = response.choices[0].message.content
            analysis_path = os.path.join(output_dir, f"{base_name}_analysis.txt")

            with open(analysis_path, "w", encoding="utf-8") as f:
                f.write(analysis_text)

            return analysis_path

        except Exception as e:
            print(f"[CallAnalytics] Error analyzing transcription: {e}")
            return None

    def answer_question(
        self,
        conversation_file: str,
        question: str,
    ) -> typing.Optional[str]:
        """Answer a specific question based on the transcription."""
        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                transcription = f.read()

            prompt = (
                f"Based on this call transcription, answer the question below:\n\n"
                f"TRANSCRIPTION:\n{transcription}\n\n"
                f"QUESTION: {question}"
            )

            response = self.client.chat.completions(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
            return response.choices[0].message.content

        except Exception as e:
            print(f"[CallAnalytics] Error answering question: {e}")
            return None

    def get_summary(
        self,
        conversation_file: str,
    ) -> typing.Optional[str]:
        """Generate a concise summary from the analysis file."""
        output_dir = os.path.dirname(conversation_file)
        base_name = os.path.basename(conversation_file).replace("_conversation.txt", "")
        analysis_path = os.path.join(output_dir, f"{base_name}_analysis.txt")

        if not os.path.exists(analysis_path):
            return None

        try:
            with open(analysis_path, "r", encoding="utf-8") as f:
                analysis_text = f.read()

            prompt_content = SUMMARY_PROMPT_TEMPLATE.format(analysis_text=analysis_text)
            messages = [
                {
                    "role": "system",
                    "content": "You are a call analytics summarizing expert. Concise answers only."
                },
                {"role": "user", "content": textwrap.dedent(prompt_content)},
            ]

            response = self.client.chat.completions(
                messages=messages,
                temperature=0.0,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"[CallAnalytics] Error generating summary: {e}")
            return None

    def grade_call(
        self,
        conversation_file: str,
        scorecard_criteria: typing.List[typing.Dict[str, typing.Any]]
    ) -> typing.Optional[typing.Dict[str, typing.Any]]:
        """Grade the call based on the provided scorecard criteria using LLM."""
        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                transcription = f.read()

            # Format criteria for the prompt
            criteria_text = ""
            for idx, item in enumerate(scorecard_criteria, 1):
                name = item.get("criteria", "Unknown")
                desc = item.get("description", "")
                criteria_text += f"{idx}. {name}: {desc}\n"

            prompt_content = GRADING_PROMPT_TEMPLATE.format(
                transcription=transcription,
                criteria_text=criteria_text
            )

            messages = [
                {
                    "role": "system",
                    "content": "You are an expert QA grader. You output strict JSON."
                },
                {"role": "user", "content": textwrap.dedent(prompt_content)},
            ]

            response = self.client.chat.completions(
                messages=messages,
                temperature=0.0,
            )
            
            content = response.choices[0].message.content
            # Clean up potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[0]
                
            return json.loads(content.strip())

        except Exception as e:
            print(f"[CallAnalytics] Error grading call: {e}")
            return None
