"""历史记录存储（V2.2）。

每仓库一个 JSON 文件（默认 {cwd}/.repo-seo-history/{owner}__{repo}.json），
按时间戳升序追加扫描快照。文件损坏时容错（备份后重建），不阻塞体检。
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class DimensionSnapshot:
    earned: float
    eligible: float
    total: float


@dataclass
class SnapshotRecord:
    at: str                       # ISO 时间
    total: float                  # 总分 0~100
    dimensions: dict[str, DimensionSnapshot]
    url: str = ""
    source: str = "monitor"       # monitor / scan
    note: str | None = None
    report: dict | None = None    # 完整评分报告（V2.3 历史版本追溯；旧记录为 None）

    def to_dict(self) -> dict:
        d = {
            "at": self.at,
            "total": self.total,
            "dimensions": {
                k: asdict(v) for k, v in self.dimensions.items()
            },
            "url": self.url,
            "source": self.source,
            "note": self.note,
        }
        if self.report is not None:
            d["report"] = self.report
        return d


def _parse_record(raw: dict) -> SnapshotRecord | None:
    try:
        dims = {}
        for k, v in (raw.get("dimensions") or {}).items():
            dims[k] = DimensionSnapshot(
                earned=float(v.get("earned", 0)),
                eligible=float(v.get("eligible", 0)),
                total=float(v.get("total", 0)),
            )
        report = raw.get("report")
        return SnapshotRecord(
            at=str(raw["at"]),
            total=float(raw["total"]),
            dimensions=dims,
            url=str(raw.get("url", "")),
            source=str(raw.get("source", "monitor")),
            note=raw.get("note"),
            report=report if isinstance(report, dict) else None,
        )
    except (KeyError, TypeError, ValueError):
        return None


def default_history_dir() -> Path:
    return Path(".repo-seo-history")


def history_path(owner: str, repo: str, base: Path | None = None) -> Path:
    base = base or default_history_dir()
    return base / f"{owner}__{repo}.json"


class HistoryStore:
    def __init__(self, base: Path | None = None) -> None:
        self.base = base or default_history_dir()
        self.base.mkdir(parents=True, exist_ok=True)

    def load(self, owner: str, repo: str) -> list[SnapshotRecord]:
        p = history_path(owner, repo, self.base)
        if not p.exists():
            return []
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            records = [r for r in (_parse_record(x) for x in raw) if r is not None]
            return sorted(records, key=lambda r: r.at)
        except (json.JSONDecodeError, OSError):
            # 文件损坏：备份后重建，不阻塞体检
            backup = p.with_suffix(".corrupt.json")
            try:
                shutil.copy2(p, backup)
            except OSError:
                pass
            return []

    def append(self, record: SnapshotRecord, owner: str, repo: str) -> None:
        records = self.load(owner, repo)
        # 同一时间戳去重（重复体检不叠加）
        if records and records[-1].at == record.at:
            records[-1] = record
        else:
            records.append(record)
        p = history_path(owner, repo, self.base)
        p.write_text(
            json.dumps([r.to_dict() for r in records], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def count(self, owner: str, repo: str) -> int:
        return len(self.load(owner, repo))
