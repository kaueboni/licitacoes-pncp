---
name: buscar-licitacoes
description: Busca licitações abertas no PNCP (Portal Nacional de Contratações Públicas) por palavra-chave e baixa editais e anexos. Use quando o usuário pedir para "buscar licitações", "procurar editais", "tem pregão de X?", "licitações abertas de Y em SP", "monitorar licitações", ou mencionar PNCP, pregão, concorrência, dispensa ou edital a encontrar.
---

# Buscar licitações no PNCP

Use as ferramentas do servidor MCP `licitacoes-pncp`.

## Fluxo

1. **Entender o filtro.** Extraia do pedido: palavra(s)-chave, UF, modalidade e status. Padrões quando não informados: `status="recebendo_proposta"`, todas as UFs, todas as modalidades. Não pergunte o que dá para inferir.
   - Códigos de modalidade úteis: 6 = Pregão Eletrônico, 8 = Dispensa, 4 = Concorrência Eletrônica, 9 = Inexigibilidade, 12 = Credenciamento.
   - Para status, aceite `recebendo_proposta`, `em_julgamento`, `encerradas` ou `todos`.

2. **Buscar** com `buscar_licitacoes`. Se o termo for amplo e vier muita coisa, refine (UF, termo mais específico) antes de despejar resultados. Se vier vazio, tente sinônimos (ex.: "merenda" → "gêneros alimentícios"; "software" → "sistema", "licença", "SaaS") e diga quais termos foram tentados.

3. **Apresentar** em tabela compacta, mais recentes primeiro:
   `# | Objeto (resumido) | Órgão – Município/UF | Modalidade | Valor estimado | Fim propostas`
   Inclua o link do PNCP de cada uma. Informe o total encontrado e se há mais páginas. Destaque prazos de proposta que vencem em até 3 dias.

4. **Aprofundar sob pedido.** Quando o usuário escolher uma licitação:
   - `detalhar_licitacao` para itens, quantidades e valores.
   - `listar_documentos` para ver edital, termo de referência e anexos.
   - `baixar_documento` (sem `sequencial_documento` baixa todos os ativos).
   - Em seguida, siga a skill **analisar-edital**.

## Observações

- Datas vêm em ISO; converta para dd/mm/aaaa hh:mm (horário de Brasília) ao mostrar.
- `valor_estimado` "não informado" pode indicar orçamento sigiloso — mencione isso.
- O PNCP é a fonte oficial, mas a disputa acontece no sistema de origem (`sistema_origem`); mostre esse link quando existir.
- Se uma chamada falhar (API fora do ar, 5xx), informe e sugira tentar de novo em alguns minutos; não invente resultados.
