from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from streamlit_conciliacao.utils import (
    get_logger,
    read_extrato,
    read_lancamentos,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
LOGGER = get_logger()


def _listar_empresas() -> Dict[str, Path]:
    """
    Retorna um dicionário mapeando CNPJ (nome da subpasta) para o caminho do arquivo JSON de configuração.
    Espera estrutura: data/<CNPJ>/contas_config.json
    """
    empresas = {}
    for subdir in DATA_DIR.iterdir():
        if subdir.is_dir():
            config_path = subdir / "contas_config.json"
            if config_path.exists():
                cnpj = subdir.name
                empresas[cnpj] = config_path
    return empresas



def _carregar_config(path: Path) -> Dict[str, Any]:
    """Lê o JSON de configuração da empresa."""
    try:
        with path.open(encoding="utf-8") as fp:
            return json.load(fp)
    except Exception as exc:  # pragma: no cover - fluxo simples
        LOGGER.error("Erro ao carregar config %s: %s", path, exc)
        return {}


def _validar_colunas(df: pd.DataFrame, colunas: list[str]) -> bool:
    """Verifica se todas as colunas estão presentes no DataFrame."""
    return all(col in df.columns for col in colunas)


def _mostrar_dataframe(df: pd.DataFrame, titulo: str) -> None:
    st.subheader(titulo)
    st.dataframe(df.head())


def main() -> None:
    st.title("Conciliação Contábil - Drogarias")

    empresas = _listar_empresas()
    opcoes = sorted(empresas.keys())
    cnpj = st.selectbox("Selecione a empresa", options=opcoes)

    if cnpj:
        config = _carregar_config(empresas[cnpj])
        st.subheader("Dados da Empresa")
        st.json(config)

    extrato_file = st.file_uploader("Extrato Bancário (.xlsx)", type=["xlsx"])
    lanc_file = st.file_uploader(
        "Planilha de Lançamentos (.xlsx)",
        type=["xlsx"],
    )

    if extrato_file is not None:
        try:
            df_extrato = read_extrato(extrato_file)
            colunas = ["Data", "Histórico", "Valor"]
            if _validar_colunas(df_extrato, colunas):
                _mostrar_dataframe(df_extrato, "Extrato Bancário")
            else:
                st.error("Colunas do extrato inválidas.")
        except Exception as exc:  # pragma: no cover - fluxo de erro
            st.error(f"Erro ao ler extrato: {exc}")

    if lanc_file is not None:
        try:
            df_lanc = read_lancamentos(lanc_file)
            colunas = [
                "Data pagamento",
                "Nome do fornecedor",
                "Nota fiscal",
                "Valor",
                "Descontos",
                "Multa e juros",
                "Valor a pagar",
                "Tarifas de Boleto",
            ]
            if _validar_colunas(df_lanc, colunas):
                _mostrar_dataframe(df_lanc, "Lançamentos")
            else:
                st.error("Colunas dos lançamentos inválidas.")
        except Exception as exc:  # pragma: no cover - fluxo de erro
            st.error(f"Erro ao ler lançamentos: {exc}")


if __name__ == "__main__":
    main()
