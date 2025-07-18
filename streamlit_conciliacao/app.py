"""Aplicação Streamlit para conciliação contábil."""

from __future__ import annotations

import json
import io
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from streamlit_conciliacao import conciliador
from streamlit_conciliacao.utils import (
    get_logger,
    read_extrato,
    read_lancamentos,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
LOGGER = get_logger()


def _listar_empresas() -> Dict[str, Path]:
    """Retorna CNPJs disponíveis mapeando para ``contas_config.json``."""
    empresas: Dict[str, Path] = {}
    for pasta in DATA_DIR.iterdir():
        if pasta.is_dir():
            cfg = pasta / "contas_config.json"
            if cfg.exists():
                empresas[pasta.name] = cfg
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
    """Exibe apenas as primeiras linhas de ``df`` com um subtítulo."""
    st.subheader(titulo)
    st.dataframe(df.head())


def main() -> None:
    """Desenha interface e executa o fluxo principal."""

    st.set_page_config(page_title="Conciliação Contábil", layout="wide")
    st.title("Conciliação Contábil - Drogarias")

    empresas = _listar_empresas()
    opcoes = sorted(empresas.keys())
    cnpj = st.selectbox("Selecione a empresa", options=opcoes)

    if not cnpj:
        st.info("Escolha uma empresa para iniciar.")
        return

    config = _carregar_config(empresas[cnpj])

    # --- Bloco: dados da empresa
    st.header("Empresa")
    st.markdown(f"**CNPJ:** {cnpj}")
    st.markdown(
        "Abaixo estão as contas cadastradas para conciliação. "
        "Utilize a busca para localizar fornecedores."
    )

    fornecedores = pd.DataFrame(
        list(config.get("fornecedores", {}).items()),
        columns=["Fornecedor", "Código da Conta"],
    )
    filtro = st.text_input("Pesquisar fornecedor")
    if filtro:
        fornecedores = fornecedores[
            fornecedores["Fornecedor"].str.contains(filtro, case=False)
        ]
    st.dataframe(fornecedores)

    contas_pagamento = config.get("contas_pagamento", {})
    contas_df = pd.DataFrame(
        list(contas_pagamento.items()),
        columns=["Conta", "Código"],
    )
    st.subheader("Contas de Pagamento")
    st.dataframe(contas_df)
    conta_nome = st.selectbox(
        "Conta bancária para conciliação",
        list(contas_pagamento.keys()),
    )
    conta_banco = contas_pagamento.get(conta_nome, 0)

    # --- Bloco: uploads
    st.header("Uploads")
    st.caption(
        "Somente as saídas (D) do extrato serão conciliadas por data e valor."
    )

    extrato_file = st.file_uploader(
        "Extrato Bancário (.xlsx)",
        type=["xlsx"],
        help="Relatório do banco contendo valores com 'D' ou 'C' no final",
    )
    if extrato_file:
        size_kb = extrato_file.size / 1024
        st.write(f"**{extrato_file.name}** - {size_kb:.1f} KB")

    lanc_file = st.file_uploader(
        "Planilha de Lançamentos (.xlsx)",
        type=["xlsx"],
        help="Planilha exportada do sistema interno",
    )
    if lanc_file:
        size_kb = lanc_file.size / 1024
        st.write(f"**{lanc_file.name}** - {size_kb:.1f} KB")

    btn_disabled = extrato_file is None or lanc_file is None
    if st.button("Conciliar e Gerar CSV", disabled=btn_disabled):
        try:
            df_extrato = read_extrato(extrato_file)
            df_lanc = read_lancamentos(lanc_file)
            if not _validar_colunas(
                df_extrato, ["Data", "Histórico", "Valor"]
            ):
                st.error("Colunas do extrato inválidas.")
                return
            colunas_lanc = [
                "Data pagamento",
                "Nome do fornecedor",
                "Nota fiscal",
                "Valor",
                "Descontos",
                "Multa e juros",
                "Valor a pagar",
                "Tarifas de Boleto",
            ]
            if not _validar_colunas(df_lanc, colunas_lanc):
                st.error("Colunas dos lançamentos inválidas.")
                return

            conciliado = conciliador.conciliar(
                df_extrato,
                df_lanc,
                config,
                conta_banco=conta_banco,
            )
            st.success("Conciliação realizada com sucesso!")
            export_df = conciliado.drop(columns="_tipo")
            _mostrar_dataframe(export_df, "Prévia do Resultado")

            csv_data = export_df.to_csv(
                sep=";", index=False, encoding="utf-8-sig"
            ).encode("utf-8-sig")
            st.download_button(
                "Baixar CSV",
                data=csv_data,
                file_name=f"conciliacao_{cnpj}.csv",
                mime="text/csv",
            )
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                export_df.to_excel(writer, index=False)
            st.download_button(
                "Baixar Excel",
                data=buffer.getvalue(),
                file_name=f"conciliacao_{cnpj}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
            )
        except Exception as exc:  # pragma: no cover - fluxo de erro
            st.error(f"Erro ao processar arquivos: {exc}")


if __name__ == "__main__":
    main()
