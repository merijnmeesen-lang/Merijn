"""Laden en valideren van de configuratie (config.yaml)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

DEFAULT_PAIRS = [
    "AUDUSD",
    "AUDJPY",
    "AUDNZD",
    "AUDCAD",
    "AUDCHF",
    "EURAUD",
    "GBPAUD",
]


@dataclass
class Config:
    pairs: list[str] = field(default_factory=lambda: list(DEFAULT_PAIRS))
    timeframe: str = "H1"
    bars_count: int = 300
    ema_fast: int = 50
    ema_slow: int = 200
    rsi_period: int = 14
    rsi_buy_threshold: float = 50.0
    rsi_sell_threshold: float = 50.0
    atr_period: int = 14
    atr_multiplier: float = 1.5
    rr_ratio: float = 2.0

    def validate(self) -> None:
        if not self.pairs:
            raise ValueError("config.pairs mag niet leeg zijn")
        if self.ema_fast <= 0 or self.ema_slow <= 0:
            raise ValueError("ema_fast en ema_slow moeten positief zijn")
        if self.ema_fast >= self.ema_slow:
            raise ValueError("ema_fast moet kleiner zijn dan ema_slow")
        if self.rsi_period <= 0:
            raise ValueError("rsi_period moet positief zijn")
        if not (0.0 <= self.rsi_buy_threshold <= 100.0):
            raise ValueError("rsi_buy_threshold moet tussen 0 en 100 liggen")
        if not (0.0 <= self.rsi_sell_threshold <= 100.0):
            raise ValueError("rsi_sell_threshold moet tussen 0 en 100 liggen")
        if self.atr_period <= 0:
            raise ValueError("atr_period moet positief zijn")
        if self.atr_multiplier <= 0:
            raise ValueError("atr_multiplier moet positief zijn")
        if self.rr_ratio <= 0:
            raise ValueError("rr_ratio moet positief zijn")
        if self.bars_count <= self.ema_slow:
            raise ValueError("bars_count moet groter zijn dan ema_slow")


def load_config(path: str | Path | None = None) -> Config:
    """Laadt de configuratie uit een YAML-bestand.

    Ontbrekende velden vallen terug op de defaults van `Config`.
    """
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH

    data: dict = {}
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

    known_fields = {f for f in Config.__dataclass_fields__}
    unknown = set(data) - known_fields
    if unknown:
        raise ValueError(f"Onbekende configsleutel(s) in {config_path}: {sorted(unknown)}")

    config = Config(**data)
    config.validate()
    return config
