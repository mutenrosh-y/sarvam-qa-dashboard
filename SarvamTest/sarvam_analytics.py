"""
CallAnalytics - Audio processing and STT via Sarvam Batch API.

Handles audio splitting, batch speech-to-text-translate with diarization,
and transcription parsing into conversation + timing outputs.
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

from pydub import AudioSegment  # noqa: E402
from sarvamai import SarvamAI  # noqa: E402


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


# ---------------------------------------------------------------------------
# Audio utilities
# ---------------------------------------------------------------------------

def split_audio(
    audio_path: str,
    chunk_duration_ms: int = 60 * 60 * 1000,  # 1 hour
    output_dir: typing.Optional[str] = None,
) -> typing.List[str]:
    """Split an audio file into chunks of *chunk_duration_ms* milliseconds.

    If the file is shorter than one chunk the original path is returned
    as-is (no copy is made).

    Parameters
    ----------
    audio_path:
        Path to the source audio file.
    chunk_duration_ms:
        Maximum duration per chunk in milliseconds (default 1 hour).
    output_dir:
        Directory to write chunks into.  When *None* a temporary
        directory is created automatically.

    Returns
    -------
    List of file paths – either the original file (when no split is
    needed) or the generated chunk files.
    """
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
# CallAnalytics
# ---------------------------------------------------------------------------

class CallAnalytics:
    """Orchestrates Sarvam STT Batch API with diarization and parses results.

    Parameters
    ----------
    client:
        An authenticated ``SarvamAI`` client instance.
    """

    def __init__(self, client: SarvamAI) -> None:
        self.client = client

    # ------------------------------------------------------------------
    # STT batch processing
    # ------------------------------------------------------------------

    def process_audio_files(
        self,
        audio_paths: typing.List[str],
        output_dir: str = "outputs",
        model: str = "saaras:v3",
        num_speakers: typing.Optional[int] = None,
    ) -> typing.Dict[str, str]:
        """Submit audio files to Sarvam STT Batch API and return parsed results.

        The method will:
        1. Split any file that exceeds 1 hour into chunks.
        2. Create a batch job with ``mode="translate"`` and
           ``with_diarization=True``.
        3. Upload, start, wait, and download results.
        4. Parse downloaded JSON into conversation + timing files.

        Parameters
        ----------
        audio_paths:
            List of local audio file paths.
        output_dir:
            Directory to store downloaded results and generated outputs.
        model:
            Sarvam STT model identifier (default ``"saaras:v3"``).
        num_speakers:
            Optional hint for the number of speakers.

        Returns
        -------
        dict with keys:
            - ``conversation_file``: path to ``_conversation.txt``
            - ``timing_file``: path to ``_timing.json``
            - ``raw_output_dir``: path to the raw JSON output directory
        """
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
            model=model,  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType]
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

        # 5. Wait for completion (poll every 5s, timeout 10 min)
        status = job.wait_until_complete(poll_interval=5, timeout=600)
        print(f"[CallAnalytics] Job finished with state: {status.job_state}")

        if status.job_state.lower() == "failed":
            raise RuntimeError(
                f"STT batch job {job.job_id} failed. "
                f"Check the Sarvam dashboard for details."
            )

        # 6. Download outputs
        raw_output_dir = os.path.join(output_dir, "raw")
        job.download_outputs(output_dir=raw_output_dir)
        print(f"[CallAnalytics] Outputs downloaded to {raw_output_dir}")

        # 7. Parse transcriptions
        result = self._parse_transcriptions(raw_output_dir, output_dir)
        return result

    # ------------------------------------------------------------------
    # Transcription parsing
    # ------------------------------------------------------------------

    def _parse_transcriptions(
        self,
        raw_output_dir: str,
        output_dir: str,
    ) -> typing.Dict[str, str]:
        """Parse downloaded STT JSON files into conversation + timing outputs.

        Reads every ``*.json`` file in *raw_output_dir*, extracts the
        ``diarized_transcript.entries`` array, and produces:

        * ``_conversation.txt`` – human-readable speaker-labelled dialogue.
        * ``_timing.json`` – total speaking duration per speaker (seconds).

        Parameters
        ----------
        raw_output_dir:
            Directory containing the raw JSON result files.
        output_dir:
            Directory where the parsed output files are written.

        Returns
        -------
        dict with ``conversation_file``, ``timing_file``, ``raw_output_dir``.
        """
        all_entries: typing.List[typing.Dict[str, typing.Any]] = []

        # Collect diarized entries from every result file
        for fname in sorted(os.listdir(raw_output_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(raw_output_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # diarized_transcript.entries is the expected structure
            diarized = data.get("diarized_transcript", {})
            entries = diarized.get("entries", [])
            all_entries.extend(entries)

            # Fallback: if no diarized data, use the plain transcript
            if not entries and "transcript" in data:
                all_entries.append({
                    "speaker_id": "SPEAKER_00",
                    "transcript": data["transcript"],
                    "start_time_seconds": 0.0,
                    "end_time_seconds": 0.0,
                })

        # Build conversation text and speaker timing
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

        # Write _conversation.txt
        conversation_file = os.path.join(output_dir, "_conversation.txt")
        with open(conversation_file, "w", encoding="utf-8") as f:
            f.write("\n".join(conversation_lines))
            f.write("\n")

        # Write _timing.json
        timing_file = os.path.join(output_dir, "_timing.json")
        with open(timing_file, "w", encoding="utf-8") as f:
            json.dump(speaker_times, f, indent=2, ensure_ascii=False)
            f.write("\n")

        print(f"[CallAnalytics] Conversation saved to {conversation_file}")
        print(f"[CallAnalytics] Timing saved to {timing_file}")
        print(f"[CallAnalytics] Speakers: {speaker_times}")

        return {
            "conversation_file": conversation_file,
            "timing_file": timing_file,
            "raw_output_dir": raw_output_dir,
        }

    # ------------------------------------------------------------------
    # LLM Analysis
    # ------------------------------------------------------------------

    def analyze_transcription(
        self,
        conversation_file: str,
        output_dir: str,
    ) -> typing.Optional[str]:
        """Analyze a transcription using LLM to extract structured insights.

        Reads the conversation file, sends it to Sarvam LLM with a detailed
        analysis prompt, and saves the result to ``_analysis.txt``.
        """
        base_name = os.path.basename(conversation_file).replace("_conversation.txt", "")
        print(f"[CallAnalytics] Analyzing transcription for {base_name}...")

        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                transcription = f.read()

            if not transcription.strip():
                print("[CallAnalytics] Empty transcription, skipping analysis.")
                return None

            prompt_content = ANALYSIS_PROMPT_TEMPLATE.format(transcription=transcription)
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a call analytics expert working for a company's support operations team. "
                        "Your job is to understand customer calls end-to-end and provide structured insights "
                        "to improve customer experience and agent effectiveness."
                    ),
                },
                {"role": "user", "content": textwrap.dedent(prompt_content)},
            ]

            # Use the default model (sarvam-2b-instruct/sarvam-m) as the SDK does not support 'model' param
            response = self.client.chat.completions(
                messages=messages,
                temperature=0.0,
            )

            analysis_text = response.choices[0].message.content
            analysis_path = os.path.join(output_dir, f"{base_name}_analysis.txt")

            with open(analysis_path, "w", encoding="utf-8") as f:
                f.write(analysis_text)

            print(f"[CallAnalytics] Analysis saved to {analysis_path}")
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
        print(f"[CallAnalytics] Answering question: {question}")
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

            answer = response.choices[0].message.content
            
            # Save answer to file for record
            q_hash = hashlib.sha1(question.encode()).hexdigest()[:6]
            output_dir = os.path.dirname(conversation_file)
            base_name = os.path.basename(conversation_file).replace("_conversation.txt", "")
            answer_path = os.path.join(output_dir, f"{base_name}_question_{q_hash}.txt")
            
            with open(answer_path, "w", encoding="utf-8") as f:
                f.write(f"Question: {question}\n\nAnswer:\n{answer}")
            
            print(f"[CallAnalytics] Answer saved to {answer_path}")
            return answer

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
            print(f"[CallAnalytics] Analysis file not found for {base_name}, cannot generate summary.")
            return None

        print(f"[CallAnalytics] Generating summary for {base_name}...")
        try:
            with open(analysis_path, "r", encoding="utf-8") as f:
                analysis_text = f.read()

            prompt_content = SUMMARY_PROMPT_TEMPLATE.format(analysis_text=analysis_text)
            messages = [
                {
                    "role": "system", 
                    "content": "You are a call analytics summarizing expert. Provide concise and clear answers to each point."
                },
                {"role": "user", "content": textwrap.dedent(prompt_content)},
            ]

            response = self.client.chat.completions(
                messages=messages,
                temperature=0.0,
            )

            concise_summary = response.choices[0].message.content.strip()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_path = os.path.join(output_dir, f"summary_{timestamp}.txt")

            with open(summary_path, "w", encoding="utf-8") as f:
                f.write("CALL ANALYTICS SUMMARY REPORT\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"Source: {base_name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(concise_summary)
                f.write("\n")

            print(f"[CallAnalytics] Summary report saved to {summary_path}")
            return concise_summary

        except Exception as e:
            print(f"[CallAnalytics] Error generating summary: {e}")
            return None


def main():
    """Main execution entry point."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("SARVAM_API_KEY")
    if not api_key:
        print("Error: SARVAM_API_KEY not found in environment variables.")
        sys.exit(1)

    client = SarvamAI(api_subscription_key=api_key)
    analytics = CallAnalytics(client)

    # CLI argument parsing (simple)
    import argparse
    parser = argparse.ArgumentParser(description="Sarvam Call Analytics Pipeline")
    parser.add_argument("--audio", help="Path to input audio file")
    parser.add_argument("--question", help="Optional question to ask about the call")
    args = parser.parse_args()

    audio_path = args.audio
    if not audio_path:
        # Default to sample if exists
        default_sample = os.path.join("samples", "Sample_product_refund.mp3")
        if os.path.exists(default_sample):
            audio_path = default_sample
        else:
            print("Usage: python sarvam_analytics.py --audio <path_to_audio>")
            sys.exit(1)

    print(f"Starting analysis pipeline for: {audio_path}")
    
    # 1. Process Audio (STT)
    # process_audio_files returns a dictionary with output paths
    results = analytics.process_audio_files([audio_path])
    conversation_file = results.get("conversation_file")
    
    if conversation_file and os.path.exists(conversation_file):
        output_dir = os.path.dirname(conversation_file)
        
        # 2. Analyze Transcription (LLM)
        analytics.analyze_transcription(conversation_file, output_dir)
        
        # 3. Answer Question (Optional)
        if args.question:
            analytics.answer_question(conversation_file, args.question)
            
        # 4. Generate Summary
        analytics.get_summary(conversation_file)
        
        print("\nPipeline Complete. Check 'outputs/' directory.")
    else:
        print("STT processing failed or produced no output.")
        sys.exit(1)


if __name__ == "__main__":
    main()
