import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit_conciliacao import cadastro  # noqa: E402


@pytest.fixture(autouse=True)
def temp_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(cadastro, "DATA_DIR", data_dir)
    yield data_dir


def test_auto_criacao_load(tmp_path):
    cnpj = "12345678901234"
    data = cadastro.load_cadastros(cnpj)
    json_path = cadastro.DATA_DIR / cnpj / "contas.json"
    assert json_path.exists()
    assert data == cadastro.DEFAULT_CADASTRO


def test_crud_fornecedor():
    cnpj = "111"
    cadastro.add_fornecedor(cnpj, "ACME", 10)
    data = cadastro.load_cadastros(cnpj)
    assert data["fornecedores"]["ACME"] == 10

    cadastro.edit_fornecedor(cnpj, "ACME", 20)
    data = cadastro.load_cadastros(cnpj)
    assert data["fornecedores"]["ACME"] == 20

    cadastro.delete_fornecedor(cnpj, "ACME")
    data = cadastro.load_cadastros(cnpj)
    assert "ACME" not in data["fornecedores"]


def test_set_conta_especial():
    cnpj = "222"
    cadastro.set_conta_especial(cnpj, "multas_juros", 99)
    data = cadastro.load_cadastros(cnpj)
    assert data["multas_juros"] == 99


def test_erros_validacao():
    cnpj = "333"
    with pytest.raises(ValueError):
        cadastro.add_item(cnpj, "invalida", "x", 1)
    with pytest.raises(ValueError):
        cadastro.set_conta_especial(cnpj, "foo", 1)
