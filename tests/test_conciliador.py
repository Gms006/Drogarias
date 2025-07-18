import sys
from pathlib import Path

import pandas as pd

# Permite importar o pacote a partir do repositório local
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit_conciliacao import conciliador  # noqa: E402


# ----------------------------------------------------------------------
# 1) Pagamento casado 1‑a‑1 com o extrato (saída D)
# ----------------------------------------------------------------------
def test_pagamento_conciliado():
    df_extrato = pd.DataFrame(
        {
            "Data": ["01/01/2024"],
            "Histórico": ["PAG"],
            "Valor": ["100,00D"],
        }
    )
    df_lanc = pd.DataFrame(
        {
            "Data pagamento": ["01/01/2024"],
            "Nome do fornecedor": ["ACME"],
            "Nota fiscal": ["123"],
            "Valor": ["100,00"],
            "Descontos": ["0,00"],
            "Multa e juros": ["0,00"],
            "Valor a pagar": ["100,00"],
            "Tarifas de Boleto": ["0,00"],
        }
    )
    config = {
        "fornecedores": {"ACME": 10},
        "contas_pagamento": {"Banco": 7},
        "multas_juros": 50,
        "descontos": 60,
    }

    result = conciliador.conciliar(df_extrato, df_lanc, config)

    # Lançamento simples gera 2 linhas (débito fornecedor, crédito banco)
    assert len(result) == 2
    assert result.iloc[0]["Cod Conta Débito"] == 10
    assert result.iloc[1]["Cod Conta Crédito"] == 7
    assert result.iloc[0]["Valor"] == "100,00"
    assert result.iloc[0]["Cod Histórico"] == 34
    assert result.iloc[0]["Complemento"] == "123 ACME"


# ----------------------------------------------------------------------
# 2) Pagamento que não casa com o extrato → vai para caixa
# ----------------------------------------------------------------------
def test_pagamento_caixa_restante():
    df_extrato = pd.DataFrame(
        {
            "Data": ["01/01/2024"],
            "Histórico": ["SAI"],
            "Valor": ["100,00D"],
        }
    )
    df_lanc = pd.DataFrame(
        {
            "Data pagamento": ["01/01/2024"],
            "Nome do fornecedor": ["ACME"],
            "Nota fiscal": ["123"],
            "Valor": ["80,00"],
            "Descontos": ["10,00"],
            "Multa e juros": ["5,00"],
            "Valor a pagar": ["75,00"],
            "Tarifas de Boleto": ["2,00"],
        }
    )
    config = {
        "fornecedores": {"ACME": 10},
        "contas_pagamento": {"Banco": 7},
        "multas_juros": 50,
        "descontos": 60,
    }

    result = conciliador.conciliar(df_extrato, df_lanc, config)

    # 1ª e 2ª linhas = extrato não conciliado (débito padrão / crédito banco)
    assert result.iloc[0]["Cod Conta Débito"] == 5
    assert result.iloc[1]["Cod Conta Crédito"] == 7

    # Lançamento em caixa começa na linha 2 (index 2)
    assert result.iloc[2]["Cod Histórico"] == 1  # COD_HISTORICO_PAG_CAIXA
    assert result.iloc[2]["Inicia Lote"] == "1"

    # Esperado: 2 linhas do extrato + 5 do lançamento composto = 7
    assert len(result) == 7


# ----------------------------------------------------------------------
# 3) Entrada de cliente (PIX recebido) — crédito C
# ----------------------------------------------------------------------
def test_entrada_cliente():
    df_extrato = pd.DataFrame(
        {
            "Data": ["02/01/2024"],
            "Histórico": ["PIX RECEBIDO - OUTRA IF"],
            "Valor": ["50,00C"],
        }
    )
    # Sem planilha de lançamentos
    df_lanc = pd.DataFrame(
        columns=[
            "Data pagamento",
            "Nome do fornecedor",
            "Nota fiscal",
            "Valor",
            "Descontos",
            "Multa e juros",
            "Valor a pagar",
            "Tarifas de Boleto",
        ]
    )
    config = {
        "contas_pagamento": {"Banco": 7},
        "clientes": {"PIX RECEBIDO - OUTRA IF": 5},
    }

    result = conciliador.conciliar(df_extrato, df_lanc, config)

    # Duas linhas: débito banco / crédito cliente
    assert len(result) == 2
    assert result.iloc[0]["Cod Conta Débito"] == 7
    assert result.iloc[1]["Cod Conta Crédito"] == 5
    assert result.iloc[0]["Valor"] == "50,00"
