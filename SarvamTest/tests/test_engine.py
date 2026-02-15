"""
Unit tests for sarvam_engine.py

Tests the SarvamEngine class, particularly the grade_call function
with mocked LLM responses.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, MagicMock, patch

# Import the engine module
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sarvam_engine import SarvamEngine, split_audio


class TestSplitAudio(unittest.TestCase):
    """Test audio splitting utility."""

    def test_split_audio_short_file(self):
        """Test that short audio files are not split."""
        # Create a temporary short audio file (< 1 hour)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Mock AudioSegment to return a short duration
            with patch("sarvam_engine.AudioSegment") as mock_audio:
                mock_instance = MagicMock()
                mock_instance.__len__.return_value = 30 * 60 * 1000  # 30 minutes
                mock_audio.from_file.return_value = mock_instance

                result = split_audio(tmp_path)

                # Should return original path unchanged
                self.assertEqual(result, [tmp_path])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_split_audio_long_file(self):
        """Test that long audio files are split into chunks."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                with patch("sarvam_engine.AudioSegment") as mock_audio:
                    # Mock a 2-hour audio file
                    mock_instance = MagicMock()
                    mock_instance.__len__.return_value = 2 * 60 * 60 * 1000  # 2 hours
                    mock_instance.__getitem__.return_value = MagicMock()
                    mock_audio.from_file.return_value = mock_instance

                    result = split_audio(tmp_path, output_dir=output_dir)

                    # Should return multiple chunks
                    self.assertGreater(len(result), 1)
                    # All chunks should be in output_dir
                    for chunk_path in result:
                        self.assertTrue(chunk_path.startswith(output_dir))
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestSarvamEngineGradeCall(unittest.TestCase):
    """Test SarvamEngine.grade_call function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.engine = SarvamEngine(self.mock_client)

    def test_grade_call_success(self):
        """Test successful call grading with mocked LLM response."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "grades": [
                {
                    "criterion": "Agent politeness",
                    "score": 5,
                    "reasoning": "Agent was very polite and professional throughout."
                },
                {
                    "criterion": "Issue resolution",
                    "score": 4,
                    "reasoning": "Agent resolved most issues but left one minor point unaddressed."
                },
                {
                    "criterion": "Call duration",
                    "score": 3,
                    "reasoning": "Call was appropriately timed for the complexity."
                }
            ],
            "overall_score": 4.0,
            "summary": "Good call with professional handling and effective resolution."
        })

        self.mock_client.chat.completions.return_value = mock_response

        # Test data
        transcript = "SPEAKER_00: Hello, how can I help?\nSPEAKER_01: I need help with my account."
        scorecard_items = ["Agent politeness", "Issue resolution", "Call duration"]

        # Call the function
        result = self.engine.grade_call(transcript, scorecard_items)

        # Assertions
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["grades"]), 3)
        self.assertEqual(result["overall_score"], 4.0)
        self.assertIn("summary", result)

        # Verify LLM was called
        self.mock_client.chat.completions.assert_called_once()

    def test_grade_call_with_markdown_json(self):
        """Test grade_call when LLM returns JSON in markdown code blocks."""
        # Mock LLM response with markdown code blocks
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
Here's the grading:

```json
{
  "grades": [
    {
      "criterion": "Agent politeness",
      "score": 5,
      "reasoning": "Very polite"
    }
  ],
  "overall_score": 5.0,
  "summary": "Excellent call"
}
```
"""

        self.mock_client.chat.completions.return_value = mock_response

        transcript = "SPEAKER_00: Hello\nSPEAKER_01: Hi"
        scorecard_items = ["Agent politeness"]

        result = self.engine.grade_call(transcript, scorecard_items)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["overall_score"], 5.0)
        self.assertEqual(len(result["grades"]), 1)

    def test_grade_call_empty_transcript(self):
        """Test grade_call with empty transcript."""
        result = self.engine.grade_call("", ["Criterion 1"])

        self.assertEqual(result["status"], "failed")
        self.assertIn("Empty transcript", result["error"])

    def test_grade_call_no_scorecard(self):
        """Test grade_call with no scorecard items."""
        transcript = "SPEAKER_00: Hello"
        result = self.engine.grade_call(transcript, [])

        self.assertEqual(result["status"], "failed")
        self.assertIn("No scorecard items", result["error"])

    def test_grade_call_with_output_dir(self):
        """Test grade_call saves results to file when output_dir provided."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "grades": [
                {
                    "criterion": "Test criterion",
                    "score": 4,
                    "reasoning": "Good performance"
                }
            ],
            "overall_score": 4.0,
            "summary": "Good call"
        })

        self.mock_client.chat.completions.return_value = mock_response

        with tempfile.TemporaryDirectory() as output_dir:
            transcript = "SPEAKER_00: Test call"
            scorecard_items = ["Test criterion"]

            result = self.engine.grade_call(transcript, scorecard_items, output_dir=output_dir)

            self.assertEqual(result["status"], "success")
            self.assertIn("grading_file", result)
            self.assertTrue(os.path.exists(result["grading_file"]))

            # Verify file content
            with open(result["grading_file"], "r") as f:
                saved_data = json.load(f)
                self.assertEqual(saved_data["overall_score"], 4.0)

    def test_grade_call_llm_error(self):
        """Test grade_call handles LLM errors gracefully."""
        self.mock_client.chat.completions.side_effect = Exception("API Error")

        transcript = "SPEAKER_00: Hello"
        scorecard_items = ["Criterion"]

        result = self.engine.grade_call(transcript, scorecard_items)

        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)


class TestSarvamEngineAnalyzeCall(unittest.TestCase):
    """Test SarvamEngine.analyze_call function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.engine = SarvamEngine(self.mock_client)

    def test_analyze_call_success(self):
        """Test successful call analysis."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis: Customer was satisfied."

        self.mock_client.chat.completions.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a conversation file
            conv_file = os.path.join(tmpdir, "test_conversation.txt")
            with open(conv_file, "w") as f:
                f.write("SPEAKER_00: Hello\nSPEAKER_01: Hi there")

            result = self.engine.analyze_call(conv_file, output_dir=tmpdir)

            self.assertEqual(result["status"], "success")
            self.assertIn("analysis_text", result)
            self.assertIn("analysis_file", result)
            self.assertTrue(os.path.exists(result["analysis_file"]))

    def test_analyze_call_empty_file(self):
        """Test analyze_call with empty conversation file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            conv_file = os.path.join(tmpdir, "test_conversation.txt")
            with open(conv_file, "w") as f:
                f.write("")

            result = self.engine.analyze_call(conv_file, output_dir=tmpdir)

            self.assertEqual(result["status"], "failed")
            self.assertIn("Empty transcription", result["error"])


class TestSarvamEngineAnswerQuestion(unittest.TestCase):
    """Test SarvamEngine.answer_question function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.engine = SarvamEngine(self.mock_client)

    def test_answer_question_success(self):
        """Test successful question answering."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The customer was satisfied with the resolution."

        self.mock_client.chat.completions.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a conversation file
            conv_file = os.path.join(tmpdir, "test_conversation.txt")
            with open(conv_file, "w") as f:
                f.write("SPEAKER_00: Hello\nSPEAKER_01: I need help")

            result = self.engine.answer_question(
                conv_file,
                "Was the customer satisfied?",
                output_dir=tmpdir
            )

            self.assertEqual(result["status"], "success")
            self.assertIn("answer", result)
            self.assertIn("answer_file", result)
            self.assertTrue(os.path.exists(result["answer_file"]))


class TestSarvamEngineTranscribeAudio(unittest.TestCase):
    """Test SarvamEngine.transcribe_audio function."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.engine = SarvamEngine(self.mock_client)

    def test_transcribe_audio_success(self):
        """Test successful audio transcription."""
        # Mock the job and its methods
        mock_job = MagicMock()
        mock_status = MagicMock()
        mock_status.job_state = "completed"
        mock_job.wait_until_complete.return_value = mock_status

        self.mock_client.speech_to_text_translate_job.create_job.return_value = mock_job

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock audio file
            audio_file = os.path.join(tmpdir, "test.wav")
            with open(audio_file, "w") as f:
                f.write("mock audio")

            # Mock the raw output directory
            raw_dir = os.path.join(tmpdir, "raw")
            os.makedirs(raw_dir, exist_ok=True)

            # Create mock JSON output
            with open(os.path.join(raw_dir, "output.json"), "w") as f:
                json.dump({
                    "diarized_transcript": {
                        "entries": [
                            {
                                "speaker_id": "SPEAKER_00",
                                "transcript": "Hello",
                                "start_time_seconds": 0.0,
                                "end_time_seconds": 1.0
                            }
                        ]
                    }
                }, f)

            # Mock split_audio to return the audio file
            with patch("sarvam_engine.split_audio") as mock_split:
                mock_split.return_value = [audio_file]

                result = self.engine.transcribe_audio([audio_file], output_dir=tmpdir)

                self.assertEqual(result["status"], "success")
                self.assertIn("conversation_file", result)
                self.assertIn("timing_file", result)

    def test_transcribe_audio_job_failed(self):
        """Test transcribe_audio when job fails."""
        mock_job = MagicMock()
        mock_status = MagicMock()
        mock_status.job_state = "failed"
        mock_job.wait_until_complete.return_value = mock_status

        self.mock_client.speech_to_text_translate_job.create_job.return_value = mock_job

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_file = os.path.join(tmpdir, "test.wav")
            with open(audio_file, "w") as f:
                f.write("mock audio")

            with patch("sarvam_engine.split_audio") as mock_split:
                mock_split.return_value = [audio_file]

                result = self.engine.transcribe_audio([audio_file], output_dir=tmpdir)

                self.assertEqual(result["status"], "failed")
                self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
