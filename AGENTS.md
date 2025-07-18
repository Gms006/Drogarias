# AGENTS.md  
Guia para Agentes (Codex / ChatGPT) – Projeto **“Conciliação Contábil Drogarias”**

> **Objetivo do repositório**  
> Automatizar a conciliação de extratos bancários × planilhas de lançamentos e
> gerar um **CSV contábil padronizado** para importação em sistemas de contabilidade,
> além de disponibilizar uma interface Web em **Streamlit**.

---

## 1. Visão geral da estrutura

| Caminho                               | Descrição rápida                                                    |
|---------------------------------------|---------------------------------------------------------------------|
| `streamlit_conciliacao/app.py`        | Interface Streamlit (upload, seleção de empresa, download).         |
| `streamlit_conciliacao/utils.py`      | Logger, leitores de Excel, exportação CSV.                          |
| `streamlit_conciliacao/cadastro.py`   | CRUD de cadastros (`data/<CNPJ>/contas.json`).                      |
| `streamlit_conciliacao/utils_git.py`  | Funções para _commit_ automático de JSON/CSV no GitHub.             |
| `data/<CNPJ>/contas_config_<CNPJ>.json`| Plano de contas, fornecedores, clientes, contas-pagamento, etc.     |
| `tests/`                              | Pytest para módulos de utilidades e cadastro.                       |
| `requirements.txt`                    | Dependências (Streamlit, pandas, PyGithub…).                        |

---

## 2. Fluxo principal que o agente deve respeitar

1. **Seleção da empresa** → carrega JSON de cadastro.  
2. **Upload de**  
   - Extrato bancário `.xlsx` (colunas: `Data`, `Histórico`, `Valor` – valores terminam com **C** (crédito) ou **D** (débito) ou vêm com sinal).  
   - Planilha de Lançamentos `.xlsx` (colunas:  
     `Data pagamento`, `Nome do fornecedor`, `Nota fiscal`, `Valor`,  
     `Descontos`, `Multa e juros`, `Valor a pagar`, `Tarifas de Boleto`).  
3. **Processamento**  
   - Casar **saídas** do extrato com lançamentos por **data+valor**.  
   - Classificar lançamentos não conciliados (pagos em caixa, saques, depósitos).  
   - Respeitar códigos de contas/histórico do JSON.  
   - Gerar DataFrame final no formato CSV padronizado:  
     `Data;Cod Conta Débito;Cod Conta Crédito;Valor;Cod Histórico;Complemento;Inicia Lote`  
4. **Interface**  
   - Mostrar contagem de: conciliados, não conciliados, saques/depósitos.  
   - Botão “**Download CSV**” (UTF-8 + `;`).  
   - Se variável `GITHUB_TOKEN` e check-box “Commitar no GitHub” estiverem
     habilitados ⇒ usar `utils_git.commit_json()`/**`commit_csv()`** para subir em
     `data/<CNPJ>/YYYYMMDD_conciliacao.csv`.  
5. **Logs** em `logs/app.log` nível INFO/ERROR.

---

## 3. Regras e prioridades contábeis

| Situação                                    | Débito                    | Crédito                  | Código Hist. | Complemento                                  |
|---------------------------------------------|---------------------------|--------------------------|--------------|----------------------------------------------|
| **Pagamento Conciliado**                    | Fornecedor                | Conta-pagamento (banco)  | 34           | Nº NF + Fornecedor                           |
| **Pagamento Caixa (não conciliado)**        | Fornecedor                | Conta Caixa (5)         | 1            | Nº NF + Fornecedor                           |
| **Multas/Juros**                            | Conta Multa/Juro (JSON)   | —                        | 34           | idem                                         |
| **Desconto**                                | —                         | Conta Desconto (JSON)    | 34           | idem                                         |
| **Tarifa**                                  | Conta Tarifa 316          | —                        | 34           | idem                                         |
| **Depósito / Recebimento**                  | Conta Banco               | Conta Cliente (JSON)     | 9            | vazio                                        |
| **Saque / Saída não conciliada**            | Conta Fornecedor (5)      | Conta Banco              | 34           | vazio                                        |

> • Para lançamentos múltiplos (juros + desconto + tarifa) use **lote = 1** na primeira linha e vazio nas subsequentes.  
> • Match múltiplo (mesmo valor/data) ⇒ usar **ordem da planilha de lançamentos**.

---

## 4. Convenções de código & git

* **Commits curtos e semânticos**: `feat:`, `fix:`, `test:`, `refactor:`, etc.  
* **Mantém cobertura de testes**. Adiciona/atualiza `tests/` sempre que criar lógica nova.  
* **Nunca** remover ou sobrescrever cadastros JSON sem motivo explícito.  
* Se adicionar nova conta/fornecedor via app, gerar PR automático.  
* Branch‐base: `main`.  Trabalhar em branches `feat/<tópico>` ou `fix/<bug>`.

---

## 5. Roadmap (para agentes)

| Etapa | Descrição | Arquivo-alvo |
|-------|-----------|--------------|
| **1** | Interface Streamlit pronta (upload, seleção, pré-visualização) | `app.py` ✅ |
| **2** | Implementar `conciliador.py` (lógica de matching + builder CSV) | `streamlit_conciliacao/conciliador.py` |
| **3** | Integração no `app.py` (botão “Conciliar”) | `app.py` |
| **4** | Botão “Commitar no GitHub” (opcional) | `app.py` + `utils_git.py` |
| **5** | Testes unitários/integração (mock dos arquivos-exemplo) | `tests/` |
| **6** | Deploy automático (Streamlit Cloud) – já configurado via GitHub Action | `.github/workflows/streamlit-cloud.yml` (TODO) |

---

## 6. Como executar localmente

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_conciliacao/app.py
Para rodar testes:

bash
Copiar
Editar
pytest -q
7. FAQ rápido
Pergunta	Resposta
Onde coloco novos JSON de empresas?	data/<CNPJ>/contas_config_<CNPJ>.json
E se faltar fornecedor?	O app indicará e poderá criá-lo (salvo no JSON).
Planilha não tem colunas esperadas?	O app mostra erro e registra no log.
Quero mudar plano de contas padrão	Edite o JSON da empresa e faça commit.

Fique à vontade para sugerir melhorias e abrir issues/PRs!
© 2025 – Projeto Drogarias / Contabilidade Neto

makefile
Copiar
Editar
::contentReference[oaicite:0]{index=0}

7/8







Fontes

Perguntar ao ChatGPT
