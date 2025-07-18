import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit_conciliacao import conciliador  # noqa: E402


def test_pagamento_conciliado():
    df_extrato = pd.DataFrame(
        {
            'Data': ['01/01/2024'],
            'Histórico': ['PAG'],
            'Valor': ['100,00D'],
        }
    )
    df_lanc = pd.DataFrame(
        {
            'Data pagamento': ['01/01/2024'],
            'Nome do fornecedor': ['ACME'],
            'Nota fiscal': ['123'],
            'Valor': ['100,00'],
            'Descontos': ['0,00'],
            'Multa e juros': ['0,00'],
            'Valor a pagar': ['100,00'],
            'Tarifas de Boleto': ['0,00'],
        }
    )
    config = {
        'fornecedores': {'ACME': 10},
        'contas_pagamento': {'Banco': 7},
        'multas_juros': 50,
        'descontos': 60,
    }
    result = conciliador.conciliar(df_extrato, df_lanc, config)
    assert len(result) == 1
    row = result.iloc[0]
    assert row['Cod Conta Débito'] == 10
    assert row['Cod Conta Crédito'] == 7
    assert row['Valor'] == '100,00'
    assert row['Cod Histórico'] == 34
    assert row['Complemento'] == '123 ACME'


def test_pagamento_caixa_restante():
    df_extrato = pd.DataFrame(
        {
            'Data': ['01/01/2024'],
            'Histórico': ['SAI'],
            'Valor': ['100,00D'],
        }
    )
    df_lanc = pd.DataFrame(
        {
            'Data pagamento': ['01/01/2024'],
            'Nome do fornecedor': ['ACME'],
            'Nota fiscal': ['123'],
            'Valor': ['80,00'],
            'Descontos': ['10,00'],
            'Multa e juros': ['5,00'],
            'Valor a pagar': ['75,00'],
            'Tarifas de Boleto': ['2,00'],
        }
    )
    config = {
        'fornecedores': {'ACME': 10},
        'contas_pagamento': {'Banco': 7},
        'multas_juros': 50,
        'descontos': 60,
    }
    result = conciliador.conciliar(df_extrato, df_lanc, config)
    # primeira linha e unica do extrato nao conciliado
    assert result.iloc[0]['Cod Conta Débito'] == 5
    assert result.iloc[0]['Cod Conta Crédito'] == 7
    # lancamento nao conciliado inicia na linha 1
    assert result.iloc[1]['Cod Histórico'] == 1
    assert result.iloc[1]['Inicia Lote'] == '1'
    assert len(result) == 6
