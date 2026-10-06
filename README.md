# licitacoes-pncp

Plugin para o Claude que busca licitações no **PNCP** (Portal Nacional de Contratações Públicas) por palavra-chave, baixa editais e anexos e analisa os documentos: resumo, prazos, checklist de habilitação, riscos e recomendação de participar ou não.

## Estrutura

```
.claude-plugin/marketplace.json     # permite instalar via "plugin marketplace add"
plugins/licitacoes-pncp/
  .claude-plugin/plugin.json
  .mcp.json                         # servidor MCP local (uv + Python)
  server/pncp_server.py             # 6 ferramentas: busca, detalhes, documentos, download, leitura
  skills/buscar-licitacoes/         # como buscar e apresentar
  skills/analisar-edital/           # roteiro de análise + checklist de referência
tests/                              # testes com API simulada (sem rede)
.github/workflows/ci.yml            # roda testes e gera o .plugin como artefato
```

## Instalação

Requer [uv](https://docs.astral.sh/uv/):
`curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) ou
`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows).

**Claude Code**

```
/plugin marketplace add <usuario>/licitacoes-pncp
/plugin install licitacoes-pncp@licitacoes-pncp
```

**Claude Desktop (Cowork)** — baixe `licitacoes-pncp.plugin` dos artefatos da última execução do CI (aba Actions) e abra no app.

Detalhes do plugin, ferramentas e exemplos: [plugins/licitacoes-pncp/README.md](plugins/licitacoes-pncp/README.md).

## Desenvolvimento

```
uv run --with "mcp>=1.2,<2" --with httpx --with pypdf --with reportlab --with pytest pytest -q
```

Endpoints usados (API pública, sem chave):

| Uso | Endpoint |
|---|---|
| Busca por palavra-chave | `GET https://pncp.gov.br/api/search/?q=...&tipos_documento=edital&status=...` |
| Dados da compra | `GET /api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}` |
| Itens | `GET /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens` |
| Arquivos | `GET /api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos[/{n}]` |

A busca é a mesma usada pelo site do PNCP e não é oficialmente documentada; pode mudar sem aviso.
