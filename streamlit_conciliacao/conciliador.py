"""Funcoes de conciliacao de extrato bancario com lancamentos."""

from __future__ import annotations

from typing import Any, List

import pandas as pd

# Constantes padrao
CONTA_FORNECEDOR_PADRAO = 5
CONTA_CAIXA = 5
COD_HISTORICO_PAGAMENTO = 34
COD_HISTORICO_PAG_CAIXA = 1
COD_HISTORICO_DEPOSITO = 9


def _parse_valor_extrato(valor: Any) -> tuple[float, str]:
    """Converte valor do extrato (ex: '123,00D') para (float, tipo)."""
    s = str(valor).strip()
    tipo = s[-1].upper()
    numero = s[:-1].replace('.', '').replace(',', '.')
    return float(numero), tipo


def _parse_valor(valor: Any) -> float:
    """Converte valor no formato brasileiro para float."""
    s = str(valor).strip()
    if not s:
        return 0.0
    return float(s.replace('.', '').replace(',', '.'))


def _fmt_valor(valor: float) -> str:
    """Formata valor float para string no formato '123,45'."""
    txt = format(valor, ',.2f')
    return txt.replace(',', 'X').replace('.', ',').replace('X', '.')


def _fmt_data(data: Any) -> str:
    """Formata data para 'dd/mm/aaaa'."""
    return pd.to_datetime(data, dayfirst=True).strftime('%d/%m/%Y')


def _get_primeira_conta(contas: dict) -> int:
    """Retorna o primeiro codigo de conta de um dicionario."""
    if not contas:
        return 0
    return next(iter(contas.values()))


def _add_lote(rows: List[dict]) -> None:
    """Se 'rows' tem mais de uma linha, marca a primeira com 'Inicia Lote'."""
    if len(rows) > 1:
        rows[0]['Inicia Lote'] = '1'


def conciliar(
    df_extrato: pd.DataFrame,
    df_lancamentos: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """Concilia saidas do extrato com lancamentos."""

    banco_conta = _get_primeira_conta(config.get('contas_pagamento', {}))
    conta_multa = config.get('multas_juros', 0)
    conta_desconto = config.get('descontos', 0)
    conta_tarifa = config.get('tarifas', 316)

    lancamentos = df_lancamentos.copy()
    lancamentos['_valor'] = lancamentos['Valor a pagar'].apply(_parse_valor)
    lancamentos['_multa'] = lancamentos['Multa e juros'].apply(_parse_valor)
    lancamentos['_desconto'] = lancamentos['Descontos'].apply(_parse_valor)
    lancamentos['_tarifa'] = lancamentos[
        'Tarifas de Boleto'
    ].apply(_parse_valor)
    lancamentos['_data'] = lancamentos['Data pagamento'].apply(_fmt_data)
    lancamentos['_matched'] = False

    resultado: List[dict] = []

    for _, row in df_extrato.iterrows():
        valor, tipo = _parse_valor_extrato(row['Valor'])
        data = _fmt_data(row['Data'])

        if tipo != 'D':
            continue

        possiveis = lancamentos[
            (lancamentos['_data'] == data)
            & (lancamentos['_valor'] == valor)
            & (~lancamentos['_matched'])
        ]
        if not possiveis.empty:
            idx = possiveis.index[0]
            lanc_row = lancamentos.loc[idx]
            lancamentos.at[idx, '_matched'] = True

            fornecedor = lanc_row['Nome do fornecedor']
            nota = lanc_row['Nota fiscal']
            codigo_forn = config.get('fornecedores', {}).get(
                fornecedor, CONTA_FORNECEDOR_PADRAO
            )
            complemento = f"{nota} {fornecedor}".strip()

            linhas = [
                {
                    'Data': data,
                    'Cod Conta Débito': codigo_forn,
                    'Cod Conta Crédito': banco_conta,
                    'Valor': _fmt_valor(valor),
                    'Cod Histórico': COD_HISTORICO_PAGAMENTO,
                    'Complemento': complemento,
                    'Inicia Lote': '',
                }
            ]
            if lanc_row['_multa'] > 0:
                linhas.append(
                    {
                        'Data': data,
                        'Cod Conta Débito': conta_multa,
                        'Cod Conta Crédito': '',
                        'Valor': _fmt_valor(lanc_row['_multa']),
                        'Cod Histórico': COD_HISTORICO_PAGAMENTO,
                        'Complemento': complemento,
                        'Inicia Lote': '',
                    }
                )
            if lanc_row['_desconto'] > 0:
                linhas.append(
                    {
                        'Data': data,
                        'Cod Conta Débito': '',
                        'Cod Conta Crédito': conta_desconto,
                        'Valor': _fmt_valor(lanc_row['_desconto']),
                        'Cod Histórico': COD_HISTORICO_PAGAMENTO,
                        'Complemento': complemento,
                        'Inicia Lote': '',
                    }
                )
            if lanc_row['_tarifa'] > 0:
                linhas.append(
                    {
                        'Data': data,
                        'Cod Conta Débito': conta_tarifa,
                        'Cod Conta Crédito': '',
                        'Valor': _fmt_valor(lanc_row['_tarifa']),
                        'Cod Histórico': COD_HISTORICO_PAGAMENTO,
                        'Complemento': complemento,
                        'Inicia Lote': '',
                    }
                )
            _add_lote(linhas)
            resultado.extend(linhas)
        else:
            resultado.append(
                {
                    'Data': data,
                    'Cod Conta Débito': CONTA_FORNECEDOR_PADRAO,
                    'Cod Conta Crédito': banco_conta,
                    'Valor': _fmt_valor(valor),
                    'Cod Histórico': COD_HISTORICO_PAGAMENTO,
                    'Complemento': '',
                    'Inicia Lote': '',
                }
            )

    restantes = lancamentos[~lancamentos['_matched']]
    for _, lanc_row in restantes.iterrows():
        data = lanc_row['_data']
        fornecedor = lanc_row['Nome do fornecedor']
        nota = lanc_row['Nota fiscal']
        codigo_forn = config.get('fornecedores', {}).get(
            fornecedor, CONTA_FORNECEDOR_PADRAO
        )
        complemento = f"{nota} {fornecedor}".strip()

        linhas = [
            {
                'Data': data,
                'Cod Conta Débito': codigo_forn,
                'Cod Conta Crédito': CONTA_CAIXA,
                'Valor': _fmt_valor(lanc_row['_valor']),
                'Cod Histórico': COD_HISTORICO_PAG_CAIXA,
                'Complemento': complemento,
                'Inicia Lote': '',
            }
        ]
        if lanc_row['_multa'] > 0:
            linhas.append(
                {
                    'Data': data,
                    'Cod Conta Débito': conta_multa,
                    'Cod Conta Crédito': '',
                    'Valor': _fmt_valor(lanc_row['_multa']),
                    'Cod Histórico': COD_HISTORICO_PAGAMENTO,
                    'Complemento': complemento,
                    'Inicia Lote': '',
                }
            )
        if lanc_row['_desconto'] > 0:
            linhas.append(
                {
                    'Data': data,
                    'Cod Conta Débito': '',
                    'Cod Conta Crédito': conta_desconto,
                    'Valor': _fmt_valor(lanc_row['_desconto']),
                    'Cod Histórico': COD_HISTORICO_PAGAMENTO,
                    'Complemento': complemento,
                    'Inicia Lote': '',
                }
            )
        if lanc_row['_tarifa'] > 0:
            linhas.append(
                {
                    'Data': data,
                    'Cod Conta Débito': conta_tarifa,
                    'Cod Conta Crédito': '',
                    'Valor': _fmt_valor(lanc_row['_tarifa']),
                    'Cod Histórico': COD_HISTORICO_PAGAMENTO,
                    'Complemento': complemento,
                    'Inicia Lote': '',
                }
            )
        _add_lote(linhas)
        resultado.extend(linhas)

    cols = [
        'Data',
        'Cod Conta Débito',
        'Cod Conta Crédito',
        'Valor',
        'Cod Histórico',
        'Complemento',
        'Inicia Lote',
    ]
    return pd.DataFrame(resultado, columns=cols)
