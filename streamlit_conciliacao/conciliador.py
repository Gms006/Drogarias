"""Funções de conciliação de extrato bancário com lançamentos."""

from __future__ import annotations

import re
from typing import Any, List, Optional

import pandas as pd

# --------------------------------------------------------------------------
# Constantes contábeis
# --------------------------------------------------------------------------
CONTA_FORNECEDOR_PADRAO = 5
CONTA_CAIXA = 5
COD_HISTORICO_PAGAMENTO = 34
COD_HISTORICO_PAG_CAIXA = 1
COD_HISTORICO_DEPOSITO = 9


# --------------------------------------------------------------------------
# Utilidades de formatação e parsing
# --------------------------------------------------------------------------
def _parse_valor_extrato(valor: Any) -> tuple[float, str]:
    """Converte valor do extrato (ex.: '123,00D') em (valor, tipo)."""
    s = str(valor).strip()
    tipo = s[-1].upper()
    numero = s[:-1].replace(".", "").replace(",", ".")
    return float(numero), tipo


def _parse_valor(valor: Any) -> float:
    """
    Converte valor brasileiro ('1.234,56') para float.

    Aceita strings vazias, ``None`` ou ``NaN`` e devolve 0.0 para
    evitar propagação de valores ausentes nas validações.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return 0.0
    s = str(valor).strip()
    if not s or s.lower() == "nan":
        return 0.0
    return float(s.replace(".", "").replace(",", "."))


def _fmt_valor(valor: float) -> str:
    """Formata float como string '123,45'."""
    return f"{valor:.2f}".replace(".", ",")


def _fmt_data(data: Any) -> str:
    """Formata datas para dd/mm/aaaa."""
    return pd.to_datetime(data, dayfirst=True).strftime("%d/%m/%Y")


def _get_primeira_conta(contas: dict) -> int:
    """Retorna o primeiro código de conta do dicionário (ou 0 se vazio)."""
    return next(iter(contas.values()), 0)


def _clean_nota(nota: Any) -> str:
    """Remove caracteres não numéricos da nota fiscal."""
    return re.sub(r"\D", "", str(nota))


# --------------------------------------------------------------------------
# Funções auxiliares para montar as partidas contábeis
# --------------------------------------------------------------------------
def _adicionar_linha(
    rows: List[dict],
    *,
    data: str,
    valor: float,
    hist: int,
    complemento: str,
    tipo: str,
    debito: Optional[int] = None,
    credito: Optional[int] = None,
) -> None:
    """Adiciona uma linha (débito/crédito) ao resultado."""
    rows.append(
        {
            "Data": data,
            "Cod Conta Débito": debito or "",
            "Cod Conta Crédito": credito or "",
            "Valor": _fmt_valor(valor),
            "Cod Histórico": hist,
            "Complemento": complemento,
            "Inicia Lote": "",
            "_tipo": tipo,
        }
    )


def _marca_lote(rows: List[dict]) -> None:
    """Define a primeira linha do lote com 'Inicia Lote' = 1."""
    if rows:
        rows[0]["Inicia Lote"] = "1"


def _balance_check(rows: List[dict]) -> None:
    """Valida se débitos = créditos no bloco atual."""
    total_deb = sum(_parse_valor(r["Valor"]) for r in rows if r["Cod Conta Débito"])
    total_cred = sum(_parse_valor(r["Valor"]) for r in rows if r["Cod Conta Crédito"])
    if round(total_deb - total_cred, 2) != 0:
        raise ValueError(
            f"Partidas não fecham: débitos {total_deb} != créditos {total_cred}"
        )


# --------------------------------------------------------------------------
# Função principal de conciliação
# --------------------------------------------------------------------------
def conciliar(
    df_extrato: pd.DataFrame,
    df_lancamentos: pd.DataFrame,
    config: dict,
    conta_banco: Optional[int] = None,
) -> pd.DataFrame:
    """
    Concilia extrato bancário (saídas “D”) com planilha de lançamentos.

    Parâmetros
    ----------
    df_extrato : DataFrame
        Colunas obrigatórias: Data, Histórico, Valor (ex.: '123,00D').
    df_lancamentos : DataFrame
        Planilha exportada do sistema interno com dados a pagar.
    config : dict
        Dicionário de configuração da empresa.
    conta_banco : int, opcional
        Código da conta bancária a creditar. Se omitido, usa a primeira conta
        de config['contas_pagamento'].
    """
    # ------------------------------------------------------------------
    # Configuração de contas
    # ------------------------------------------------------------------
    banco_conta = conta_banco or _get_primeira_conta(
        config.get("contas_pagamento", {})
    )
    conta_multa = config.get("multas_juros", 0)
    conta_desconto = config.get("descontos", 0)
    conta_tarifa = config.get("tarifas", 316)

    # ------------------------------------------------------------------
    # Pré-processamento da planilha de lançamentos
    # ------------------------------------------------------------------
    lanc = df_lancamentos.copy()
    lanc["_valor_nota"] = lanc["Valor"].apply(_parse_valor)
    lanc["_valor_pagar"] = lanc["Valor a pagar"].apply(_parse_valor)
    lanc["_multa"] = lanc["Multa e juros"].apply(_parse_valor)
    lanc["_desconto"] = lanc["Descontos"].apply(_parse_valor)
    lanc["_tarifa"] = lanc["Tarifas de Boleto"].apply(_parse_valor)
    lanc["_data"] = lanc["Data pagamento"].apply(_fmt_data)
    lanc["_matched"] = False

    resultado: List[dict] = []

    # ------------------------------------------------------------------
    # 1) Percorrer o extrato e casar cada saída 'D'
    # ------------------------------------------------------------------
    for _, ext in df_extrato.iterrows():
        valor, tipo = _parse_valor_extrato(ext["Valor"])
        data = _fmt_data(ext["Data"])

        # Ignora créditos
        if tipo != "D":
            continue

        possiveis = lanc[
            (lanc["_data"] == data)
            & (lanc["_valor_pagar"] == valor)
            & (~lanc["_matched"])
        ]

        # 1.a) Encontrou match na planilha
        if not possiveis.empty:
            idx = possiveis.index[0]
            row = lanc.loc[idx]
            lanc.at[idx, "_matched"] = True

            fornecedor = row["Nome do fornecedor"]
            conta_forn = config.get("fornecedores", {}).get(
                fornecedor, CONTA_FORNECEDOR_PADRAO
            )
            nota = _clean_nota(row["Nota fiscal"])
            compl = f"{nota} {fornecedor}".strip()

            linhas: List[dict] = []
            extras = (
                row["_multa"] > 0 or row["_desconto"] > 0 or row["_tarifa"] > 0
            )

            if not extras:
                # Lançamento simples
                _adicionar_linha(
                    linhas,
                    data=data,
                    valor=row["_valor_pagar"],
                    hist=COD_HISTORICO_PAGAMENTO,
                    complemento=compl,
                    debito=conta_forn,
                    credito=banco_conta,
                    tipo="Banco",
                )
            else:
                # Lançamento composto
                _adicionar_linha(
                    linhas,
                    data=data,
                    valor=row["_valor_nota"],
                    hist=COD_HISTORICO_PAGAMENTO,
                    complemento=compl,
                    debito=conta_forn,
                    tipo="Banco",
                )
                if row["_multa"] > 0:
                    _adicionar_linha(
                        linhas,
                        data=data,
                        valor=row["_multa"],
                        hist=COD_HISTORICO_PAGAMENTO,
                        complemento=compl,
                        debito=conta_multa,
                        tipo="Banco",
                    )
                if row["_tarifa"] > 0:
                    _adicionar_linha(
                        linhas,
                        data=data,
                        valor=row["_tarifa"],
                        hist=COD_HISTORICO_PAGAMENTO,
                        complemento=compl,
                        debito=conta_tarifa,
                        tipo="Banco",
                    )
                if row["_desconto"] > 0:
                    _adicionar_linha(
                        linhas,
                        data=data,
                        valor=row["_desconto"],
                        hist=COD_HISTORICO_PAGAMENTO,
                        complemento=compl,
                        credito=conta_desconto,
                        tipo="Banco",
                    )
                _adicionar_linha(
                    linhas,
                    data=data,
                    valor=valor,
                    hist=COD_HISTORICO_PAGAMENTO,
                    complemento=compl,
                    credito=banco_conta,
                    tipo="Banco",
                )

            _marca_lote(linhas)
            _balance_check(linhas)
            resultado.extend(linhas)

        # 1.b) Sem match → usa conta padrão
        else:
            linhas: List[dict] = []
            _adicionar_linha(
                linhas,
                data=data,
                valor=valor,
                hist=COD_HISTORICO_PAGAMENTO,
                complemento="",
                debito=CONTA_FORNECEDOR_PADRAO,
                credito=banco_conta,
                tipo="Extrato",
            )
            _marca_lote(linhas)
            _balance_check(linhas)
            resultado.extend(linhas)

    # ------------------------------------------------------------------
    # 2) Lançamentos não conciliados → pagamento em caixa
    # ------------------------------------------------------------------
    restantes = lanc[~lanc["_matched"]]
    for _, row in restantes.iterrows():
        data = row["_data"]
        fornecedor = row["Nome do fornecedor"]
        conta_forn = config.get("fornecedores", {}).get(
            fornecedor, CONTA_FORNECEDOR_PADRAO
        )
        nota = _clean_nota(row["Nota fiscal"])
        compl = f"{nota} {fornecedor}".strip()

        linhas: List[dict] = []
        extras = (
            row["_multa"] > 0 or row["_desconto"] > 0 or row["_tarifa"] > 0
        )

        if not extras:
            _adicionar_linha(
                linhas,
                data=data,
                valor=row["_valor_pagar"],
                hist=COD_HISTORICO_PAG_CAIXA,
                complemento=compl,
                debito=conta_forn,
                credito=CONTA_CAIXA,
                tipo="Caixa",
            )
        else:
            _adicionar_linha(
                linhas,
                data=data,
                valor=row["_valor_nota"],
                hist=COD_HISTORICO_PAG_CAIXA,
                complemento=compl,
                debito=conta_forn,
                tipo="Caixa",
            )
            if row["_multa"] > 0:
                _adicionar_linha(
                    linhas,
                    data=data,
                    valor=row["_multa"],
                    hist=COD_HISTORICO_PAGAMENTO,
                    complemento=compl,
                    debito=conta_multa,
                    tipo="Caixa",
                )
            if row["_tarifa"] > 0:
                _adicionar_linha(
                    linhas,
                    data=data,
                    valor=row["_tarifa"],
                    hist=COD_HISTORICO_PAGAMENTO,
                    complemento=compl,
                    debito=conta_tarifa,
                    tipo="Caixa",
                )
            if row["_desconto"] > 0:
                _adicionar_linha(
                    linhas,
                    data=data,
                    valor=row["_desconto"],
                    hist=COD_HISTORICO_PAGAMENTO,
                    complemento=compl,
                    credito=conta_desconto,
                    tipo="Caixa",
                )
            _adicionar_linha(
                linhas,
                data=data,
                valor=row["_valor_pagar"] + row["_tarifa"],
                hist=COD_HISTORICO_PAG_CAIXA,
                complemento=compl,
                credito=CONTA_CAIXA,
                tipo="Caixa",
            )

        _marca_lote(linhas)
        _balance_check(linhas)
        resultado.extend(linhas)

    # ------------------------------------------------------------------
    # 3) DataFrame final
    # ------------------------------------------------------------------
    cols = [
        "Data",
        "Cod Conta Débito",
        "Cod Conta Crédito",
        "Valor",
        "Cod Histórico",
        "Complemento",
        "Inicia Lote",
        "_tipo",
    ]
    return pd.DataFrame(resultado, columns=cols)
