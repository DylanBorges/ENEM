# Proveniência de Dados e Auditoria

## Origem dos Microdados Oficiais

- Os microdados são baixados do portal oficial do Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira (INEP).
- Cada lote de microdados possui um manifesto em `pipelines/inep/manifests/YYYY.yaml`.
- O hash criptográfico SHA-256 é verificado obrigatoriamente antes de qualquer processamento.

## Direitos Autorais e Licenciamento

- Enunciados de questões e imagens originais não são redistribuídos sem revisão prévia de direitos autorais (Lei nº 9.610/1998).
- O sistema modela a estrutura estatística (item_id, área, caderno, parâmetros $a, b, c$) independente da hospedagem de enunciados.
- Todo código foi desenvolvido de forma original a partir de literatura acadêmica, evitando qualquer contaminação por licenças restritivas.
