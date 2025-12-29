import argparse
import sys
from pathlib import Path
from typing import List, Dict

# Ensure workspace root is importable when running as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.python_check import check_python_env
from tools.ffmpeg_check import check_ffmpeg
from tools.audio_check import check_audio
from tools.video_check import check_video
from tools.gpu_check import check_gpu
from tools.captions_check import check_captions
from tools.report import SummaryRow, render_table, write_json_report, collect_system_info


def main():
    parser = argparse.ArgumentParser(description="Pre-flight environment checker for crypto shorts pipeline")
    parser.add_argument("--yes", action="store_true", help="Auto-install missing Python packages without prompt")
    parser.add_argument("--report", default="setup_report.json", help="Output JSON report path")
    args = parser.parse_args()

    rows: List[SummaryRow] = []
    report: Dict = {"system": collect_system_info(), "components": {}}

    # A) Python env + packages
    py_res = check_python_env(auto_install=args.yes)
    rows.append(SummaryRow(py_res.component, py_res.status, py_res.notes))
    report["components"][py_res.component] = py_res.details

    # C) FFmpeg
    ff_res = check_ffmpeg()
    rows.append(SummaryRow(ff_res.component, ff_res.status, ff_res.notes))
    report["components"][ff_res.component] = ff_res.details

    # E) Captions validation
    cap_res = check_captions()
    rows.append(SummaryRow(cap_res.component, cap_res.status, cap_res.notes))
    report["components"][cap_res.component] = cap_res.details

    # F) Video generation (tiny test)
    vid_res = check_video()
    rows.append(SummaryRow(vid_res.component, vid_res.status, vid_res.notes))
    report["components"][vid_res.component] = vid_res.details

    # D) Audio/TTS (Piper)
    aud_res = check_audio()
    rows.append(SummaryRow(aud_res.component, aud_res.status, aud_res.notes))
    report["components"][aud_res.component] = aud_res.details

    # G) GPU optional
    gpu_res = check_gpu()
    rows.append(SummaryRow(gpu_res.component, gpu_res.status, gpu_res.notes))
    report["components"][gpu_res.component] = gpu_res.details

    table = render_table(rows)
    print(table)

    write_json_report(args.report, report)

    # PASS/FAIL summary
    hard_fail_components = [r.component for r in rows if r.status == "FAILED" or r.status == "MISSING"]
    if hard_fail_components:
        print("\n❌ FIX REQUIRED: " + ", ".join(hard_fail_components))
        print("See", args.report, "for details.")
        exit(1)
    else:
        print("\n✅ READY TO RUN PIPELINE (pre-flight passed)")
        print("Report written to", args.report)
        exit(0)


if __name__ == "__main__":
    main()
