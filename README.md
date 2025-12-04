# Diarizer – Audio Transcription & Call Analysis

This project bundles speaker diarization, speech-to-text, conversational summarisation, and qualitative call scoring into a single FastAPI web app. Upload an audio call and the app automatically:

- separates the speakers (NeMo diarization),
- transcribes each segment (Whisper Hindi2Hinglish Prime),
- produces a structured summary and sentiment report (LangChain + custom LLM),
- evaluates the call against a configurable QA checklist, and
- exposes speaker statistics, downloadable transcripts, and the original audio.

The UI (served from `audio_transcriber/templates/index.html`) is a fully client-side experience built with vanilla JS and CSS.

## Features

- **Audio upload & playback** – drag-and-drop support, inline audio player in the results screen, downloadable original audio.
- **Speaker diarization** – NeMo diarization pipeline wrapped behind `audio_processing/nemo_diarize.py`.
- **Transcription** – Whisper ASR tuned for Hindi ↔ Hinglish.
- **Summaries & sentiment** – LangChain prompt (`AudioTranscriber.summarize`) generates summary, key points, action items, roles, and tone analysis.
- **Quality evaluation** – `CallEvaluator` scores the call against weighted questions that can be managed via the UI (`/api/questions` CRUD).
- **Reporting** – Downloadable transcript, consolidated report (`downloadAll()`), plus JSON snapshots under `audio_transcriber/data/`.
- **Extensible questions** – Editable categories, JSON import/export, and ordering.

## Project Structure

```
audio_transcriber/
├── app.py                 # FastAPI entrypoint + APIs
├── templates/index.html   # Single-page UI
├── static/css/style.css   # Dark theme styling
├── static/js/app.js       # Front-end logic (upload, polling, rendering)
├── transcriber.py         # Diarization + ASR + summary helpers
├── evaluator.py           # Call scoring logic
├── audio_processing/…     # NeMo utilities and helpers
└── data/                  # Custom question storage
```

Top-level helpers (`main.py`, `run_test.py`, etc.) are provided for experimentation, but the FastAPI app is the primary interface.

## Requirements

- Python 3.11 (project ships with a `venv/` example; create your own virtualenv if cloning fresh).
- FFmpeg (for torchaudio to decode varied formats).
- GPU not required but recommended (Whisper will fallback to CPU/MPS automatically).
- Hugging Face access token (set `HF_TOKEN=<your_token>` or provide it through another secrets manager before starting the app).

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the App

```bash
# export HF_TOKEN before running (or use a .env loader)
export HF_TOKEN=<your_hf_token>
cd audio_transcriber
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in your browser. The UI walks you through uploading audio and monitoring progress.

## Workflow Overview

1. **Upload** (`POST /upload`) – validates file type, persists under `audio_transcriber/uploads/`, returns `job_id`.
2. **Process** (`POST /process/{job_id}`) – kicks off background task:
   - load models,
   - diarize (`AudioTranscriber.run_diarization`),
   - transcribe each segment with per-segment progress callbacks,
   - summarise and evaluate with enabled questions,
   - compute speaker stats.
3. **Poll status** (`GET /status/{job_id}`) – UI polls every second to update progress bars.
4. **Results** – when complete, the response contains transcript, summary, evaluation, stats, and `audio_url` for inline playback/download.

## Customising QA Questions

The UI’s “Manage Questions” modal drives the `/api/questions` endpoints. Changes persist to `audio_transcriber/data/custom_questions.json`. Use import/export to move configurations between environments or click “Reset to Defaults” to fall back to `questions_config.py`.

## Useful Commands

| Task                       | Command / Endpoint                        |
|---------------------------|-------------------------------------------|
| Health check              | `GET /health`                              |
| List QA questions         | `GET /api/questions`                       |
| Add question              | `POST /api/questions` (JSON body)          |
| Delete processed job      | `DELETE /job/{job_id}`                     |
| Stream original audio     | `GET /audio/{job_id}` (`?download=1`)      |

## Notes & Tips

- Be mindful of NumPy versions: NeMo diarization currently needs NumPy ≤ 2.2 (see warning in `transcriber._load_diarization`).
- Uploaded files are not auto-purged when deleting a job; ensure cleanup if storage is limited.
- The summariser uses a local Qwen endpoint (see `ChatOpenAI` base URL); adjust `AudioTranscriber.summarize` if you deploy different LLM infrastructure.
- For production use, consider moving the Hugging Face token to an environment variable and enabling authentication on the FastAPI app.

Happy analysing! Feel free to open issues or extend the evaluator with additional scoring logic.

