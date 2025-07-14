"""Utilitários gerais da aplicação.

Inclui funções de leitura de planilhas, geração de CSV padronizado e
configuração de logger.
"""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any

import pandas as pd


_LOGGER_NAME = "app"


def get_logger() -> logging.Logger:
    """Retorna um logger configurado.

    O logger grava em ``logs/app.log`` com rotação diária e nível INFO.
    """
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = TimedRotatingFileHandler(
            logs_dir / "app.log",
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(" "asctime)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def _read_excel(path: Path) -> pd.DataFrame:
    return pd.read_excel(path, engine="openpyxl")


def read_extrato(path: Path) -> pd.DataFrame:
    """Lê arquivo de extrato bancário em Excel."""
    return _read_excel(path)


def read_lancamentos(path: Path) -> pd.DataFrame:
    """Lê planilha de lançamentos em Excel."""
    return _read_excel(path)


def to_csv_padronizado(df: pd.DataFrame, path: Path) -> None:
    """Salva ``df`` em CSV usando ``;`` e ``utf-8-sig``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")

