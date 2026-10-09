"""File readers that turn an uploaded file (path or file-like object) into a raw DataFrame."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from os import PathLike
from typing import IO, Any

import pandas as pd

FileLike = str | PathLike[str] | IO[Any]


def _file_name(file: FileLike) -> str:
    return str(getattr(file, "name", file)).lower()


class DataSource(ABC):
    @abstractmethod
    def can_handle(self, file: FileLike) -> bool: ...

    @abstractmethod
    def read(self, file: FileLike) -> pd.DataFrame: ...


@dataclass
class CsvSource(DataSource):
    sep: str = ","

    def can_handle(self, file: FileLike) -> bool:
        return _file_name(file).endswith(".csv")

    def read(self, file: FileLike) -> pd.DataFrame:
        return pd.read_csv(file, sep=self.sep)


@dataclass
class JsonSource(DataSource):
    record_path: str | None = None

    def can_handle(self, file: FileLike) -> bool:
        return _file_name(file).endswith(".json")

    def read(self, file: FileLike) -> pd.DataFrame:
        if hasattr(file, "read"):
            data = json.load(file)
        else:
            with open(file, encoding="utf-8") as fh:
                data = json.load(fh)
        return pd.json_normalize(self._records(data))

    def _records(self, data: Any) -> list[Any]:
        if isinstance(data, list):
            return data
        if self.record_path is not None:
            return data[self.record_path]
        array_keys = [k for k, v in data.items() if isinstance(v, list)]
        if len(array_keys) != 1:
            raise ValueError(f"Cannot auto-detect record_path among {array_keys}; set it explicitly")
        return data[array_keys[0]]
