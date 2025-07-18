"""Funcoes de conciliacao de extrato bancario com lancamentos."""

from __future__ import annotations

import re
from typing import Any, List, Optional

import pandas as pd

# Constantes padrao
CONTA_FORNECEDOR_PADRAO = 5
CONTA_CAIXA = 5
COD_HISTORICO_PAGAMENTO = 34
COD_HISTORICO_PAG_CAIXA = 1
COD_HISTORICO_DEPOSITO = 9


def _parse_valor_extrato(valor: Any) -> tuple[float, str]:
    """Converte valor do extrato (ex: '123,00D') para ``(float, tipo)``."""
    s = str(valor).strip()
    tipo = s[-1].upper()
    numero = s[:-1].replace('.', '').replace(',', '.')
    return float(numero), tipo


def _parse_valor(valor: Any) -> float:
    """Converte valor em formato brasileiro para ``float``.

    ``valor`` pode ser ``NaN`` ou string vazia. Nesses casos retornamos ``0.0``
    para evitar propagação de ``NaN`` nas validações de partidas.
    """
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return 0.0
    s = str(valor).strip()
    if not s or s.lower() == "nan":
        return 0.0
    return float(s.replace(".", "").replace(",", "."))


def _fmt_valor(valor: float) -> str:
    """Formata valor ``float`` para ``'123,45'`` sem pontos."""
    return f"{valor:.2f}".replace('.', ',')


def _fmt_data(data: Any) -> str:
    """Formata data para ``dd/mm/aaaa``."""
    return pd.to_datetime(data, dayfirst=True).strftime('%d/%m/%Y')


def _get_primeira_conta(contas: dict) -> int:
    """Retorna o primeiro código de conta de ``contas``."""
    return next(iter(contas.values()), 0)


def _clean_nota(nota: Any) -> str:
    """Mantém apenas números da nota fiscal."""
    return re.sub(r"\D", "", str(nota))


def _adicionar_linha(
    rows: List[dict],
    *,
    data: str,
    valor: float,
    hist: int,
    complemento: str,
    debito: Optional[int] = None,
    credito: Optional[int] = None,
    tipo: str,
) -> None:
    """Acrescenta uma linha na estrutura de resultado."""
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
    """Marca a primeira linha do lote."""
    if rows:
        rows[0]["Inicia Lote"] = "1"


def _balance_check(rows: List[dict]) -> None:
    """Garante que a soma dos débitos é igual aos créditos."""
    total_deb = sum(
        _parse_valor(r["Valor"]) for r in rows if r["Cod Conta Débito"]
    )
    total_cred = sum(
        _parse_valor(r["Valor"]) for r in rows if r["Cod Conta Crédito"]
    )
    if round(total_deb - total_cred, 2) != 0:
        msg = (
            "Partidas não fecham: "
            f"débitos {total_deb} != créditos {total_cred}"
        )
        raise ValueError(msg)


def conciliar(
    df_extrato: pd.DataFrame,
    df_lancamentos: pd.DataFrame,
    config: dict,
    conta_banco: Optional[int] = None,
) -> pd.DataFrame:
    """Gera lançamentos contábeis conciliando extrato e planilha."""

    banco_conta = conta_banco or _get_primeira_conta(
        config.get("contas_pagamento", {})
    )
    conta_multa = config.get("multas_juros", 0)
    conta_desconto = config.get("descontos", 0)
    conta_tarifa = config.get("tarifas", 316)

    lanc = df_lancamentos.copy()
    lanc["_valor_nota"] = lanc["Valor"].apply(_parse_valor)
    lanc["_valor_pagar"] = lanc["Valor a pagar"].apply(_parse_valor)
    lanc["_multa"] = lanc["Multa e juros"].apply(_parse_valor)
    lanc["_desconto"] = lanc["Descontos"].apply(_parse_valor)
    lanc["_tarifa"] = lanc["Tarifas de Boleto"].apply(_parse_valor)
    lanc["_data"] = lanc["Data pagamento"].apply(_fmt_data)
    lanc["_matched"] = False

    resultado: List[dict] = []

    # --- percorre extrato procurando correspondência nos lançamentos
    for _, ext in df_extrato.iterrows():
        valor, tipo = _parse_valor_extrato(ext["Valor"])
        data = _fmt_data(ext["Data"])
        if tipo != "D":
            continue

        possiveis = lanc[
            (lanc["_data"] == data)
            & (lanc["_valor_pagar"] == valor)
            & (~lanc["_matched"])
        ]
        if not possiveis.empty:
            idx = possiveis.index[0]
            row = lanc.loc[idx]
            lanc.at[idx, "_matched"] = True
            fornecedor = row["Nome do fornecedor"]
            conta_forn = config.get("fornecedores", {}).get(
                fornecedor,
                CONTA_FORNECEDOR_PADRAO,
            )
            nota = _clean_nota(row["Nota fiscal"])
            compl = f"{nota} {fornecedor}".strip()

            linhas: List[dict] = []
            extras = (
                row["_multa"] > 0
                or row["_desconto"] > 0
                or row["_tarifa"] > 0
            )
            if not extras:
                # lancamento simples: debito fornecedor, credito banco
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
        else:
            # saída não conciliada do extrato
            linhas = []
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

    # --- lançamentos que não casaram com o extrato -> caixa
    restantes = lanc[~lanc["_matched"]]
    for _, row in restantes.iterrows():
        data = row["_data"]
        fornecedor = row["Nome do fornecedor"]
        conta_forn = config.get("fornecedores", {}).get(
            fornecedor,
            CONTA_FORNECEDOR_PADRAO,
        )
        nota = _clean_nota(row["Nota fiscal"])
        compl = f"{nota} {fornecedor}".strip()

        linhas: List[dict] = []
        extras = (
            row["_multa"] > 0
            or row["_desconto"] > 0
            or row["_tarifa"] > 0
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
