from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd

# Phase 2 (Indicators/Features)
from analysis.indicators import calculate_indicators
from analysis.features import calculate_features
from analysis.utils import combine_and_clean

# Phase 3 (Patterns)
from analysis.patterns import detect_patterns

# Phase 4 (ML Ranking)
from analysis.ml.labels import compute_future_labels, compute_event_labels
from analysis.ml.dataset import create_event_dataset, validate_event_dataset
from analysis.ml.model import create_model
from analysis.ml.train import time_aware_split, prepare_training_data, train_model
from analysis.ml.rank import prepare_events_for_scoring, score_events, rank_events

# Phase 5 (Charts)
from visuals import FrameConfig, generate_multi_event_frames, get_default_style

# Phase 6 (Video)
from video.assemble import assemble_video
from video.config import VideoConfig

# Phase 7 (Voiceover)
from audio.pipeline import assemble_voiceover_video
from audio.config import AudioConfig
from audio.scripts import EventMeta

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    max_events: int = 3
    lookahead_candles: int = 10
    min_rank_score: float = 0.65
    max_events_per_pattern: int = 5
    frames_per_event: int = 60
    fps: int = 30

    # Paths
    raw_csv: Path = Path("data/raw/BTC_USDT_1h.csv")
    frames_out_base: Path = Path("visuals/frames")
    video_base_dir: Path = Path("video/base")
    video_final_dir: Path = Path("video/final")
    work_dir: Path = Path("work")


def run_data_prep(cfg: PipelineConfig) -> pd.DataFrame:
    df = pd.read_csv(cfg.raw_csv, parse_dates=["timestamp"])
    ind_df = calculate_indicators(df)
    feat_df = calculate_features(pd.concat([df, ind_df], axis=1))
    final_df = combine_and_clean(df, ind_df, feat_df, drop_na=True)
    return final_df


def run_pattern_detection(df: pd.DataFrame, cfg: PipelineConfig) -> List[Dict[str, Any]]:
    events = detect_patterns(df, symbol=cfg.symbol)
    return events


def run_ml_ranking(df: pd.DataFrame, events: List[Dict[str, Any]], cfg: PipelineConfig) -> pd.DataFrame:
    df_labeled = compute_future_labels(df, lookahead_candles=cfg.lookahead_candles)
    events_labeled = compute_event_labels(df_labeled, events, lookahead_candles=cfg.lookahead_candles)

    event_dataset, feature_cols = create_event_dataset(df_labeled, events_labeled)
    if not validate_event_dataset(event_dataset, feature_cols):
        raise RuntimeError("Event dataset validation failed")

    X, y = prepare_training_data(event_dataset, feature_cols)
    X_train, X_test, y_train, y_test = time_aware_split(X, y, test_size=0.2)
    model = create_model(model_type="random_forest", n_estimators=50)
    train_model(model, X_train, y_train, X_test, y_test)

    scoring_df = prepare_events_for_scoring(events_labeled, df_labeled, feature_cols)
    scored_df = score_events(model, scoring_df, feature_cols)
    ranked_df = rank_events(scored_df, min_score=cfg.min_rank_score, max_events_per_pattern=cfg.max_events_per_pattern)
    return ranked_df


def run_chart_frames(df: pd.DataFrame, ranked_df: pd.DataFrame, cfg: PipelineConfig) -> Dict[str, tuple[int, Path]]:
    cfg.frames_out_base.mkdir(parents=True, exist_ok=True)
    frame_cfg = FrameConfig(
        frames_per_event=cfg.frames_per_event,
        show_volume=True,
        show_ema=[20, 50, 200],
        highlight_event=True,
        style=get_default_style(),
    )

    events_list = []
    for _, row in ranked_df.head(cfg.max_events).iterrows():
        events_list.append({
            "event_index": int(row["event_index"]),
            "pattern": row["pattern"],
            "ml_score": float(row.get("ml_score", 0.0)),
        })

    results = generate_multi_event_frames(
        df,
        events_list,
        cfg.frames_out_base,
        config=frame_cfg,
        max_events=cfg.max_events,
    )
    return results


def run_video(results: Dict[str, tuple[int, Path]], cfg: PipelineConfig) -> Dict[str, Path]:
    cfg.video_base_dir.mkdir(parents=True, exist_ok=True)

    outputs: Dict[str, Path] = {}
    vcfg = VideoConfig(fps=cfg.fps)
    for event_id, (num_frames, frames_dir) in results.items():
        out_path = cfg.video_base_dir / f"{event_id}.mp4"
        assemble_video(frames_dir, out_path, fps=cfg.fps, config=vcfg)
        outputs[event_id] = out_path
    return outputs


def run_voice(event_id: str, silent_mp4: Path, cfg: PipelineConfig, acfg: AudioConfig | None = None) -> Dict[str, str]:
    # Event meta for narration (simplified from ranked info)
    # In a fuller pipeline, pass actual direction/move_pct from analysis
    # Simple heuristics for direction; in a full implementation use ranked_df details
    direction = "bullish" if "BULL" in event_id.upper() or "UP" in event_id.upper() else "bearish" if "BEAR" in event_id.upper() or "DOWN" in event_id.upper() else "bullish"
    meta = EventMeta(
        event_id=event_id,
        coin=cfg.symbol.split("/")[0],
        pattern_name="Pattern",
        direction=direction,
        move_pct=2.5,
        timeframe=cfg.timeframe,
    )
    work_dir = cfg.work_dir / event_id
    final_mp4 = cfg.video_final_dir / f"{event_id}.mp4"
    cfg.video_final_dir.mkdir(parents=True, exist_ok=True)
    results = assemble_voiceover_video(meta, silent_mp4, final_mp4, work_dir, acfg or AudioConfig())
    return results


def run_approval(manifest: Dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path


def run_upload(final_videos: Dict[str, Path], upload_dir: Path) -> Dict[str, Path]:
    upload_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, Path] = {}
    for event_id, mp4 in final_videos.items():
        dest = upload_dir / mp4.name
        # In lieu of real upload, copy to uploads folder
        data = mp4.read_bytes()
        dest.write_bytes(data)
        result[event_id] = dest
    return result


def run_pipeline(cfg: PipelineConfig, audio_cfg: AudioConfig | None = None) -> Dict[str, Any]:
    logger.info("Starting pipeline")
    df = run_data_prep(cfg)
    events = run_pattern_detection(df, cfg)
    ranked = run_ml_ranking(df, events, cfg)

    frames = run_chart_frames(df, ranked, cfg)
    silent_videos = run_video(frames, cfg)

    final_videos: Dict[str, Path] = {}
    voice_results: Dict[str, Dict[str, str]] = {}

    for event_id, silent in silent_videos.items():
        voice_info = run_voice(event_id, silent, cfg, audio_cfg)
        voice_results[event_id] = voice_info
        final_videos[event_id] = Path(voice_info["final_mp4"]) if "final_mp4" in voice_info else cfg.video_final_dir / f"{event_id}.mp4"

    manifest = {
        "symbol": cfg.symbol,
        "timeframe": cfg.timeframe,
        "events": list(frames.keys()),
        "final_videos": {k: str(v) for k, v in final_videos.items()},
    }

    approval_path = Path("approvals") / "latest_manifest.json"
    run_approval(manifest, approval_path)

    uploads = run_upload(final_videos, Path("uploads"))

    return {
        "manifest": str(approval_path),
        "uploads": {k: str(v) for k, v in uploads.items()},
        "final_videos": {k: str(v) for k, v in final_videos.items()},
    }
