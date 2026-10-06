---
name: analisar-edital
description: Analisa edital de licitação e seus anexos (termo de referência, minuta de contrato, planilhas) baixados do PNCP ou enviados pelo usuário, gerando resumo executivo, checklist de habilitação, prazos, riscos e recomendação de participar ou não. Use quando o usuário pedir para "analisar o edital", "resumir a licitação", "o que precisa para participar", "quais documentos de habilitação", "vale a pena participar?", "riscos do edital", ou anexar um PDF de edital.
---

# Analisar edital de licitação

## 1. Obter o texto

- **Documento baixado pelo plugin:** use o campo `texto` retornado por `baixar_documento` (ou `listar_baixados` para achar). Leia com `ler_documento` em blocos de ~40.000 caracteres até `tem_mais=false`. Para editais longos, primeiro use `ler_documento(..., buscar="...")` com os termos da seção 3 para localizar as cláusulas-chave, depois leia os trechos completos necessários.
- **PDF escaneado** (aviso "praticamente sem texto"): abra o PDF original com a ferramenta de leitura de arquivos para leitura visual, página a página.
- **Arquivo anexado pelo usuário:** leia diretamente.
- Leia também termo de referência e minuta de contrato quando existirem; muitos requisitos técnicos e penalidades estão neles, não no edital.

## 2. Ler com método

Não resuma de memória nem por amostragem. Anote cada requisito com a referência da cláusula (ex.: "item 8.4.2") e a página quando disponível. Se algo não for encontrado, registre "não localizado no edital" em vez de supor.

## 3. Pontos obrigatórios

Consulte `references/checklist-edital.md` para o roteiro completo. No mínimo, extraia:

- **Identificação:** órgão, número, modalidade, critério de julgamento, modo de disputa, SRP (sim/não), lei de regência (14.133/2021 ou outra).
- **Objeto e itens/lotes:** o que é, quantidades, valor estimado (ou sigiloso).
- **Prazos:** abertura/sessão, limite de propostas, impugnação e esclarecimentos, validade da proposta, prazo de entrega/execução, vigência do contrato.
- **Habilitação:** jurídica, fiscal/trabalhista, econômico-financeira (índices, capital/patrimônio líquido mínimo), técnica (atestados, quantitativos mínimos, profissionais, visita técnica).
- **Participação:** exclusividade ou cota para ME/EPP, consórcio, subcontratação, vedações.
- **Proposta:** o que deve conter, amostras, catálogos, garantia de proposta.
- **Contrato:** garantia contratual, reajuste, pagamento, penalidades e multas, local de entrega.

## 4. Sinais de alerta

Marque explicitamente como **risco** cláusulas como: prazo de entrega curto, exigência de atestado com quantitativo acima de 50% do objeto, índices econômicos acima do usual (> 1,0 sem justificativa), marca específica sem "ou similar", amostra com prazo exíguo, multas altas, pagamento acima de 30 dias, garantia elevada, visita técnica obrigatória, exigências que pareçam restringir competição. Indique quando caberia pedido de esclarecimento ou impugnação, com o prazo para isso. Não afirme ilegalidade; aponte como ponto a verificar com o jurídico.

## 5. Entregar

Formato padrão da resposta:

1. **Resumo executivo** (3–5 linhas): o que é, valor, prazo de proposta, recomendação preliminar.
2. **Datas-chave** em tabela, com contagem de dias até cada uma (use a data atual).
3. **Checklist de habilitação** como lista de verificação, com cláusula de referência.
4. **Riscos e pontos de atenção**, do mais grave ao menos grave.
5. **Recomendação go / no-go** com justificativa, e perguntas que o usuário precisa responder sobre a própria empresa (ex.: tem atestado de X? patrimônio líquido ≥ Y?).

Se o usuário descrever o perfil da empresa (CNAE, porte, atestados, faturamento), cruze com os requisitos e diga item a item se atende, não atende ou precisa verificar.

Se o usuário quiser guardar a análise, ofereça gerar um documento.

Inclua sempre ao final: análise de apoio, não substitui revisão jurídica do edital.
