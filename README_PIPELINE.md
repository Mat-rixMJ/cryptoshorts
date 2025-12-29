# End-to-End Pipeline: Data → Indicators → Patterns → ML Ranking → Charts → Video → Voice → Approval → Upload

This pipeline stitches together all phases to produce ready-to-upload vertical videos with voiceover and captions.

## Prerequisites

- Python 3.10+ (venv recommended)
- FFmpeg installed and in PATH
- Piper TTS installed; download a voice model (.onnx)
- Data file: `data/raw/BTC_USDT_1h.csv`

## Quick Start

1. Create `audio_config.json` based on `audio_config.sample.json` and set `piper_exe` and `piper_model`.
2. Run the pipeline:

```powershell
& venv\Scripts\python.exe run_pipeline.py --symbol BTC/USDT --timeframe 1h --max_events 2 --frames 60 --fps 30 --audio_config audio_config.json
```

## Outputs

- Frames: `visuals/frames/{EVENT_ID}/0001.png ...`
- Silent MP4: `video/base/{EVENT_ID}.mp4`
- Voiceover work: `work/{EVENT_ID}/voice_raw.wav`, `voice_norm.wav`, `captions.srt`
- Final MP4: `video/final/{EVENT_ID}.mp4`
- Approval manifest: `approvals/latest_manifest.json`
- Uploads (simulated): `uploads/{EVENT_ID}.mp4`

## Notes

- Ranking thresholds and frames per event are configurable in the CLI.
- Captioning is deterministic; Whisper alignment can be added later.
- Upload step currently copies to `uploads/`; integrate with YouTube API if desired.
