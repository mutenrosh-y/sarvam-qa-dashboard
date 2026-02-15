# SarvamEngine Usage Examples

## Basic Setup

```python
from sarvam_engine import SarvamEngine
from sarvamai import SarvamAI
import os

# Initialize the engine
api_key = os.getenv("SARVAM_API_KEY")
if not api_key:
    raise ValueError("SARVAM_API_KEY environment variable not set")

client = SarvamAI(api_subscription_key=api_key)
engine = SarvamEngine(client)
```

## Example 1: Complete Call Processing Pipeline

```python
# 1. Transcribe audio with diarization
result = engine.transcribe_audio(
    audio_paths=["call_recording.mp3"],
    output_dir="outputs",
    num_speakers=2
)

if result["status"] != "success":
    print(f"Transcription failed: {result['error']}")
    exit(1)

conversation_file = result["conversation_file"]
print(f"Transcription saved to: {conversation_file}")

# 2. Analyze the call
analysis_result = engine.analyze_call(
    conversation_file=conversation_file,
    output_dir="outputs"
)

if analysis_result["status"] == "success":
    print("Analysis:")
    print(analysis_result["analysis_text"])
else:
    print(f"Analysis failed: {analysis_result['error']}")

# 3. Answer specific questions
question = "Was the customer satisfied with the resolution?"
qa_result = engine.answer_question(
    conversation_file=conversation_file,
    question=question,
    output_dir="outputs"
)

if qa_result["status"] == "success":
    print(f"\nQ: {question}")
    print(f"A: {qa_result['answer']}")
```

## Example 2: Call Grading (NEW)

```python
# Read the transcription
with open("outputs/_conversation.txt", "r") as f:
    transcript = f.read()

# Define grading criteria
scorecard = [
    "Agent politeness and professionalism",
    "Issue identification and understanding",
    "Problem resolution effectiveness",
    "Customer satisfaction",
    "Call efficiency (appropriate duration)",
    "Knowledge and expertise demonstrated",
    "Follow-up actions clarity"
]

# Grade the call
grading_result = engine.grade_call(
    transcript=transcript,
    scorecard_items=scorecard,
    output_dir="outputs"
)

if grading_result["status"] == "success":
    print(f"Overall Score: {grading_result['overall_score']:.1f}/5.0")
    print(f"\nSummary: {grading_result['summary']}\n")
    
    print("Detailed Grades:")
    for grade in grading_result["grades"]:
        print(f"  • {grade['criterion']}: {grade['score']}/5")
        print(f"    Reasoning: {grade['reasoning']}\n")
    
    print(f"Full results saved to: {grading_result['grading_file']}")
else:
    print(f"Grading failed: {grading_result['error']}")
```

## Example 3: Batch Processing Multiple Calls

```python
import json
from pathlib import Path

# Process multiple calls
audio_files = [
    "calls/call_001.mp3",
    "calls/call_002.mp3",
    "calls/call_003.mp3"
]

scorecard = [
    "Agent professionalism",
    "Issue resolution",
    "Customer satisfaction"
]

results = []

for audio_file in audio_files:
    print(f"Processing {audio_file}...")
    
    # Transcribe
    trans_result = engine.transcribe_audio([audio_file], output_dir="outputs")
    if trans_result["status"] != "success":
        print(f"  ❌ Transcription failed: {trans_result['error']}")
        continue
    
    # Grade
    with open(trans_result["conversation_file"], "r") as f:
        transcript = f.read()
    
    grade_result = engine.grade_call(
        transcript=transcript,
        scorecard_items=scorecard,
        output_dir="outputs"
    )
    
    if grade_result["status"] == "success":
        results.append({
            "file": audio_file,
            "overall_score": grade_result["overall_score"],
            "summary": grade_result["summary"]
        })
        print(f"  ✅ Score: {grade_result['overall_score']:.1f}/5.0")
    else:
        print(f"  ❌ Grading failed: {grade_result['error']}")

# Save batch results
with open("batch_results.json", "w") as f:
    json.dump(results, f, indent=2)

# Print summary
print(f"\nProcessed {len(results)} calls successfully")
avg_score = sum(r["overall_score"] for r in results) / len(results)
print(f"Average score: {avg_score:.1f}/5.0")
```

## Example 4: Custom Grading for Specific Scenarios

### Sales Call Grading
```python
sales_scorecard = [
    "Product knowledge demonstration",
    "Customer needs identification",
    "Value proposition clarity",
    "Objection handling",
    "Closing technique effectiveness",
    "Upsell/cross-sell opportunity recognition"
]

sales_grade = engine.grade_call(
    transcript=transcript,
    scorecard_items=sales_scorecard,
    output_dir="outputs/sales_calls"
)
```

### Support Call Grading
```python
support_scorecard = [
    "Problem understanding",
    "Troubleshooting methodology",
    "Solution clarity",
    "First-contact resolution",
    "Customer empathy",
    "Documentation of resolution"
]

support_grade = engine.grade_call(
    transcript=transcript,
    scorecard_items=support_scorecard,
    output_dir="outputs/support_calls"
)
```

### Customer Service Grading
```python
service_scorecard = [
    "Greeting and tone",
    "Active listening",
    "Response time",
    "Issue resolution",
    "Politeness and respect",
    "Willingness to help"
]

service_grade = engine.grade_call(
    transcript=transcript,
    scorecard_items=service_scorecard,
    output_dir="outputs/service_calls"
)
```

## Example 5: Error Handling

```python
def safe_grade_call(engine, transcript, scorecard):
    """Safely grade a call with error handling."""
    
    # Validate inputs
    if not transcript or not transcript.strip():
        return {"status": "failed", "error": "Empty transcript"}
    
    if not scorecard or len(scorecard) == 0:
        return {"status": "failed", "error": "Empty scorecard"}
    
    # Grade the call
    result = engine.grade_call(
        transcript=transcript,
        scorecard_items=scorecard,
        output_dir="outputs"
    )
    
    # Handle results
    if result["status"] == "success":
        return {
            "success": True,
            "score": result["overall_score"],
            "grades": result["grades"],
            "summary": result["summary"]
        }
    else:
        return {
            "success": False,
            "error": result["error"]
        }

# Usage
result = safe_grade_call(engine, transcript, scorecard)
if result["success"]:
    print(f"Score: {result['score']}")
else:
    print(f"Error: {result['error']}")
```

## Example 6: Analyzing Grading Results

```python
import json

# Load grading results
with open("outputs/grading_20240215_170000.json", "r") as f:
    grading = json.load(f)

# Extract insights
print("=== CALL GRADING REPORT ===\n")
print(f"Overall Score: {grading['overall_score']:.1f}/5.0")
print(f"Summary: {grading['summary']}\n")

# Find strengths (score >= 4)
strengths = [g for g in grading['grades'] if g['score'] >= 4]
if strengths:
    print("Strengths:")
    for grade in strengths:
        print(f"  ✓ {grade['criterion']}: {grade['score']}/5")

# Find areas for improvement (score < 3)
improvements = [g for g in grading['grades'] if g['score'] < 3]
if improvements:
    print("\nAreas for Improvement:")
    for grade in improvements:
        print(f"  ✗ {grade['criterion']}: {grade['score']}/5")
        print(f"    → {grade['reasoning']}")

# Find average scores by criterion
print("\nDetailed Breakdown:")
for grade in grading['grades']:
    bar = "█" * grade['score'] + "░" * (5 - grade['score'])
    print(f"  {grade['criterion']:.<40} {bar} {grade['score']}/5")
```

## Return Value Structures

### `transcribe_audio()` Success Response
```json
{
  "status": "success",
  "conversation_file": "/path/to/_conversation.txt",
  "timing_file": "/path/to/_timing.json",
  "raw_output_dir": "/path/to/raw"
}
```

### `analyze_call()` Success Response
```json
{
  "status": "success",
  "analysis_text": "Detailed analysis...",
  "analysis_file": "/path/to/_analysis.txt"
}
```

### `answer_question()` Success Response
```json
{
  "status": "success",
  "answer": "Answer to the question...",
  "answer_file": "/path/to/_question_abc123.txt"
}
```

### `grade_call()` Success Response
```json
{
  "status": "success",
  "grades": [
    {
      "criterion": "Agent politeness",
      "score": 5,
      "reasoning": "Agent was very polite..."
    }
  ],
  "overall_score": 4.5,
  "summary": "Overall assessment...",
  "grading_file": "/path/to/grading_20240215_170000.json"
}
```

### Error Response (All Functions)
```json
{
  "status": "failed",
  "error": "Descriptive error message"
}
```

## Tips & Best Practices

1. **Always check `status` field** before accessing other fields
2. **Use `output_dir` parameter** to organize results by call type or date
3. **Customize scorecard items** for your specific use case
4. **Batch process** for efficiency when handling multiple calls
5. **Save grading results** for audit trails and trend analysis
6. **Use consistent scorecard** across calls for comparable results
7. **Handle errors gracefully** - all functions return error dicts, not exceptions
