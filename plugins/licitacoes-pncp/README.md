# licitacoes-pncp

Plugin para o Claude que busca licitações no **PNCP** (Portal Nacional de Contratações Públicas) por palavra-chave, baixa editais e anexos e analisa os documentos.

## O que vem no plugin

| Componente | O que faz |
|---|---|
| Servidor MCP `licitacoes-pncp` | Conecta na API pública do PNCP (sem chave) |
| Skill `buscar-licitacoes` | Busca, filtra e apresenta licitações |
| Skill `analisar-edital` | Resumo, prazos, checklist de habilitação, riscos e go/no-go |

### Ferramentas do servidor

- `buscar_licitacoes(palavra_chave, status, uf, modalidade, ...)`
- `detalhar_licitacao(cnpj, ano, sequencial)` — dados e itens
- `listar_documentos(cnpj, ano, sequencial)`
- `baixar_documento(cnpj, ano, sequencial, sequencial_documento?)` — descompacta ZIPs e extrai texto de PDF/DOCX
- `ler_documento(caminho, inicio, tamanho, buscar?)` — leitura em blocos ou busca por termo
- `listar_baixados()`

## Requisitos

- [uv](https://docs.astral.sh/uv/) instalado (ele baixa Python e as dependências automaticamente na primeira execução):
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Funciona no Claude Desktop (Cowork) e no Claude Code — o servidor roda no seu computador.

## Configuração opcional

- `LICITACOES_DIR` — pasta onde os arquivos são salvos (padrão: `~/Licitacoes`).

## Exemplos de uso

- "Busca pregões abertos de merenda escolar em MG"
- "Tem licitação de licença de software em SP com prazo nesta semana?"
- "Baixa o edital da 2ª e analisa: o que preciso para participar?"
- "Minha empresa é EPP, PL de R$ 300 mil, tenho atestado de 10 mil refeições/mês. Atendo?"

## Limitações

- PDFs escaneados não têm texto extraível; o Claude lê o PDF original visualmente.
- A busca usa o mesmo mecanismo do site do PNCP, que não é uma API oficialmente documentada e pode mudar.
- A análise é apoio; não substitui revisão jurídica.
