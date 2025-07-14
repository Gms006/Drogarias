### streamlit_conciliacao/cadastro.py
"""CRUD de contas e fornecedores em arquivos JSON."""

from __future__ import annotations

import json
from pathlib import Path

# Diretório base para os dados
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

# Estrutura padrão de cada arquivo contas.json
DEFAULT_CADASTRO = {
    "fornecedores": {},
    "contas_pagamento": {},
    "multas_juros": 0,
    "tarifas": 0,
    "descontos": 0,
}

VALID_CATEGORIAS = {"fornecedores", "contas_pagamento"}
VALID_CAMPOS_ESPECIAIS = {"multas_juros", "tarifas", "descontos"}


def get_empresa_path(cnpj: str) -> Path:
    """Retorna o diretório data/<CNPJ>, criando-o se necessário."""
    path = DATA_DIR / cnpj
    path.mkdir(parents=True, exist_ok=True)
    return path


def _get_json_path(cnpj: str) -> Path:
    """Retorna o caminho completo para o JSON de cadastros da empresa."""
    return get_empresa_path(cnpj) / "contas.json"


def load_cadastros(cnpj: str) -> dict:
    """Carrega o JSON da empresa. Se não existir, cria estrutura padrão."""
    json_path = _get_json_path(cnpj)
    if not json_path.exists():
        data: dict = DEFAULT_CADASTRO.copy()
        save_cadastros(cnpj, data)
        return data
    with json_path.open(encoding="utf-8") as fp:
        return json.load(fp)


def save_cadastros(cnpj: str, data: dict) -> None:
    """Salva (indentado=2, ensure_ascii=False) o JSON da empresa."""
    json_path = _get_json_path(cnpj)
    tmp_path = json_path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
    tmp_path.replace(json_path)


# --------------------------------------------------------------------------- #
# Operações CRUD genéricas                                                    #
# --------------------------------------------------------------------------- #
def _validar_categoria(categoria: str) -> None:
    """Valida se a categoria é permitida."""
    if categoria not in VALID_CATEGORIAS:
        raise ValueError(f"Categoria inválida: {categoria}")


def add_item(cnpj: str, categoria: str, chave: str, valor: int) -> None:
    """Adiciona um item à categoria especificada."""
    _validar_categoria(categoria)
    data = load_cadastros(cnpj)
    data[categoria][chave] = valor
    save_cadastros(cnpj, data)


def edit_item(cnpj: str, categoria: str, chave: str, novo_valor: int) -> None:
    """Edita um item existente na categoria."""
    _validar_categoria(categoria)
    data = load_cadastros(cnpj)
    if chave not in data[categoria]:
        raise KeyError(chave)
    data[categoria][chave] = novo_valor
    save_cadastros(cnpj, data)


def delete_item(cnpj: str, categoria: str, chave: str) -> None:
    """Remove um item da categoria."""
    _validar_categoria(categoria)
    data = load_cadastros(cnpj)
    if chave not in data[categoria]:
        raise KeyError(chave)
    del data[categoria][chave]
    save_cadastros(cnpj, data)


# --------------------------------------------------------------------------- #
# Atalhos específicos                                                         #
# --------------------------------------------------------------------------- #
def add_fornecedor(cnpj: str, nome: str, codigo: int) -> None:
    """Atalho para adicionar fornecedor."""
    add_item(cnpj, "fornecedores", nome, codigo)


def edit_fornecedor(cnpj: str, nome: str, novo_codigo: int) -> None:
    """Atalho para editar fornecedor."""
    edit_item(cnpj, "fornecedores", nome, novo_codigo)


def delete_fornecedor(cnpj: str, nome: str) -> None:
    """Atalho para remover fornecedor."""
    delete_item(cnpj, "fornecedores", nome)


def set_conta_especial(cnpj: str, campo: str, codigo: int) -> None:
    """Define o código de conta para campos especiais."""
    if campo not in VALID_CAMPOS_ESPECIAIS:
        raise ValueError(f"Campo inválido: {campo}")
    data = load_cadastros(cnpj)
    data[campo] = codigo
    save_cadastros(cnpj, data)
