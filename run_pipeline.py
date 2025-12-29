"""
Main Orchestrator Script
Runs Phase 1 → Phase 8 sequentially
"""

import logging
from pathlib import Path
import yaml

# -----------------------
# IMPORT PHASE MODULES
# -----------------------

# Phase 1
from data.fetch import fetch_data

# Phase 2
from analysis.indicators import add_indicators
from analysis.features import add_features

# Phase 3
from analysis.patterns import detect_patterns

# Phase 4
from analysis.ml.rank import rank_events
from analysis.ml.labels import compute_future_labels, compute_event_labels
from analysis.ml.dataset import create_event_dataset, validate_event_dataset
from analysis.ml.model import create_model
from analysis.ml.train import time_aware_split, prepare_training_data, train_model
from analysis.ml.rank import prepare_events_for_scoring, score_events

# Phase 5
from visuals.frames import generate_frames_for_event, FrameConfig, get_default_style

# Phase 6
from video.assemble import assemble_video_for_event

# Phase 7
from audio.scripts import generate_script
from audio.tts import generate_voice
from audio.captions import generate_captions
from audio.merge import merge_audio_video

# Phase 8
from publish.telegram_bot import send_preview
from publish.approval import wait_for_approval
from publish.youtube_uploader import upload_video


# -----------------------
# SETUP
# -----------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

ROOT = Path(__file__).parent


# -----------------------
# LOAD CONFIG
# -----------------------

def load_config():
    with open(ROOT / "config.yaml", "r") as f:
        return yaml.safe_load(f)


# -----------------------
# MAIN PIPELINE
# -----------------------

def run_pipeline():
    config = load_config()

    symbols = config.get("symbols") or config.get("coins") or ["BTC/USDT"]
    timeframe = config.get("timeframe", "1h")
    events_per_coin = int(config.get("events_per_coin", 2))
    candle_limit = int(config.get("candle_limit", 500))
    exchange = config.get("exchange", "binance")

    # Audio settings from config.yaml
    audio_cfg_yaml = (config.get("audio") or {})
    burn_captions_flag = bool(audio_cfg_yaml.get("burn_captions", True))

    for symbol in symbols:
        logging.info(f"🚀 Processing {symbol}")

        # -----------------------
        # PHASE 1: DATA
        # -----------------------
        df = fetch_data(symbol, timeframe, limit=candle_limit, exchange=exchange)

        # -----------------------
        # PHASE 2: FEATURES
        # -----------------------
        df = add_indicators(df)
        df = add_features(df)

        # -----------------------
        # PHASE 3: PATTERNS
        # -----------------------
        pattern_config = {
            "ema": True,
            "rsi": True,
            "breakout": True,
            "volume": True,
            "structure": True,
        }
        events = detect_patterns(df, config=pattern_config, symbol=symbol)

        if not events:
            logging.info("No events found")
            continue

        # -----------------------
        # PHASE 4: ML RANKING (train lightweight model inline)
        # -----------------------
        # Compute labels for training
        lookahead = 10
        df_labeled = compute_future_labels(df, lookahead_candles=lookahead)
        events_labeled = compute_event_labels(df_labeled, events, lookahead_candles=lookahead)

        event_dataset, feature_cols = create_event_dataset(df_labeled, events_labeled)
        if not validate_event_dataset(event_dataset, feature_cols):
            logging.info("Event dataset invalid; skipping")
            continue

        X, y = prepare_training_data(event_dataset, feature_cols)
        X_train, X_test, y_train, y_test = time_aware_split(X, y, test_size=0.2)
        model = create_model(model_type="random_forest", n_estimators=50)
        train_model(model, X_train, y_train, X_test, y_test)

        scoring_df = prepare_events_for_scoring(events_labeled, df_labeled, feature_cols)
        scored_df = score_events(model, scoring_df, feature_cols)
        ranked_events_df = rank_events(scored_df, min_score=0.65, max_events_per_pattern=5)

        selected_events = ranked_events_df.head(events_per_coin).to_dict(orient="records")

        for event in selected_events:
            event_id = event.get("event_id") or f"event_{event['event_index']:03d}_{event['pattern'][:3]}"
            event["event_id"] = event_id
            event["symbol"] = symbol
            event["timeframe"] = timeframe

            logging.info(f"🎯 Event selected: {event_id}")

            # -----------------------
            # PHASE 5: FRAMES
            # -----------------------
            frames_dir = generate_frames_for_event(df, event)

            # -----------------------
            # PHASE 6: VIDEO
            # -----------------------
            base_video = assemble_video_for_event(frames_dir=frames_dir, event_id=event_id, fps=30)

            # -----------------------
            # PHASE 7: AUDIO + CAPTIONS (skip if Piper not available)
            # -----------------------
            try:
                # Auto-load audio config from audio/audio_config.json
                audio_cfg_path = ROOT / "audio" / "audio_config.json"
                from audio.config import load_audio_config, AudioConfig
                acfg = load_audio_config(audio_cfg_path)
                logging.info("audio_config_loaded enabled=%s burn_captions=%s", acfg.enabled, burn_captions_flag)

                script = generate_script(event)
                voice_path = generate_voice(script, event_id, cfg=acfg)
                captions_path = generate_captions(script, event_id, cfg=acfg)

                # Ensure we pass a Path even if voice is None (merge handles missing audio)
                audio_path = voice_path if voice_path is not None else (ROOT / "work" / event_id / "voice_norm.wav")

                final_video = merge_audio_video(
                    video_path=base_video,
                    audio_path=audio_path,
                    captions_path=captions_path,
                    event_id=event_id,
                    cfg=acfg,
                    burn_captions=burn_captions_flag,
                )
            except Exception as e:
                logging.warning(f"Voiceover skipped due to error: {e}")
                final_video = base_video

            # -----------------------
            # PHASE 8: PREVIEW + UPLOAD
            # -----------------------
            send_preview(final_video, event)

            approved = wait_for_approval(event_id)

            if approved and (config.get("youtube", {}).get("enabled", False)):
                upload_video(final_video, event)
                logging.info("✅ Uploaded to YouTube")
            else:
                logging.info("⏸ Upload skipped")

    logging.info("🎉 Pipeline finished")


# -----------------------
# ENTRY POINT
# -----------------------

if __name__ == "__main__":
    run_pipeline()
