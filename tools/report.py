import json
import platform
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class SummaryRow:
    component: str
    status: str
    notes: str


def render_table(rows: List[SummaryRow]) -> str:
    # Simple console table
    col1 = max(len(r.component) for r in rows + [SummaryRow("Component", "Status", "Notes")])
    col2 = max(len(r.status) for r in rows + [SummaryRow("Component", "Status", "Notes")])
    header = f"{'Component'.ljust(col1)} | {'Status'.ljust(col2)} | Notes"
    sep = "-" * len(header)
    lines = [header, sep]
    for r in rows:
        lines.append(f"{r.component.ljust(col1)} | {r.status.ljust(col2)} | {r.notes}")
    return "\n".join(lines)


def write_json_report(path: str, data: Dict) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def collect_system_info() -> Dict:
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "machine": platform.machine(),
    }
