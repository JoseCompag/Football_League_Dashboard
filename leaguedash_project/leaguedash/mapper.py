"""Map arbitrary file columns onto the canonical schema and coerce types."""

import json
from dataclasses import dataclass

import pandas as pd

from leaguedash.schema import FieldRegistry, field_registry


@dataclass
class MappingResult:
    matches: pd.DataFrame
    skipped_rows: int
    warnings: list[str]


class ColumnMapper:
    def __init__(self, mapping: dict[str, str | None] | None = None, registry: FieldRegistry = field_registry) -> None:
        self.mapping: dict[str, str | None] = dict(mapping or {})
        self.registry = registry

    def suggest(self, df: pd.DataFrame) -> dict[str, str | None]:
        """Case-insensitive match of each field's key + aliases against the file's columns."""
        by_lower = {str(col).lower(): str(col) for col in df.columns}
        return {
            f.key: next((by_lower[name.lower()] for name in [f.key, *f.aliases] if name.lower() in by_lower), None)
            for f in self.registry.all()
        }

    def validate(self) -> list[str]:
        return [f"Required field '{f.label}' is not mapped" for f in self.registry.required() if not self.mapping.get(f.key)]

    def apply(self, df: pd.DataFrame) -> MappingResult:
        errors = self.validate()
        if errors:
            raise ValueError("; ".join(errors))
        fields = [f for f in self.registry.all() if self.mapping.get(f.key)]
        out = pd.DataFrame({f.key: df[self.mapping[f.key]] for f in fields}, index=df.index)
        warnings: list[str] = []

        for f in fields:
            if f.dtype == "int":
                out[f.key] = pd.to_numeric(out[f.key], errors="coerce")
            elif f.dtype == "datetime":
                parsed = pd.to_datetime(out[f.key], errors="coerce")
                bad_dates = int((parsed.isna() & out[f.key].notna()).sum())
                if bad_dates:
                    warnings.append(f"{bad_dates} unparseable value(s) in '{f.label}' set to empty")
                out[f.key] = parsed
            else:
                out[f.key] = out[f.key].astype("string").str.strip()

        int_keys = [f.key for f in fields if f.dtype == "int" and f.required]
        kept = out.dropna(subset=int_keys)
        skipped = len(out) - len(kept)
        if skipped:
            warnings.append(f"{skipped} row(s) skipped: non-numeric or missing values in {', '.join(int_keys)}")

        matches = kept.astype({k: "int64" for k in int_keys})
        matches.insert(0, "match_id", matches.index)
        return MappingResult(matches.reset_index(drop=True), skipped, warnings)

    def to_json(self) -> str:
        return json.dumps(self.mapping, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "ColumnMapper":
        return cls(json.loads(text))
