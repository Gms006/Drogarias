# Conciliação Contábil – Drogarias

Este projeto tem como objetivo simplificar o processo de conciliação contábil para drogarias. A aplicação web, desenvolvida com Streamlit, possibilitará o upload de planilhas de extrato bancário e lançamentos contábeis, realizando a análise linha a linha para identificar pagamentos realizados via banco ou caixa. Regras de aplicação de multas, descontos e tarifas serão tratadas automaticamente.

Após a conciliação, será gerado um arquivo CSV padronizado para importação em sistemas contábeis. O sistema manterá informações de contas e fornecedores em arquivos JSON agrupados por CNPJ, além de disponibilizar logs e relatórios em uma aba dedicada.

## Estrutura de Pastas

- `streamlit_conciliacao/` &ndash; Código da aplicação e módulos auxiliares.
- `tests/` &ndash; Casos de teste a serem desenvolvidos.
- `data/` &ndash; Contém subpastas por CNPJ e respectivos arquivos JSON.
- `logs/` &ndash; Guarda arquivos de log da aplicação.
- `requirements.txt` &ndash; Dependências do projeto.

## Instalação Rápida

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Detalhes completos de configuração e execução serão fornecidos nos próximos fragmentos.
