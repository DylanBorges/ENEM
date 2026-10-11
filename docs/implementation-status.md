# Estado verificável da implementação (11/10/2026)

## Diagnóstico

O monorepo contém FastAPI/SQLAlchemy, `tri_core` puro com 3PL e EAP, pipeline de microdados, worker Celery e frontend Next.js. A suíte usa dados sintéticos nos testes; a aplicação regular de 2025 agora usa parâmetros de itens publicados pelo Inep e uma transformação de escala ajustada e verificada contra resultados reais. A estimativa do produto continua não oficial. O antigo script de seed criava parâmetros, gabaritos e métricas inventados para 2025; foi removido, e o registro que restava no banco local foi desativado e preservado em backup antes da substituição.

## Entrega desta etapa

- O frontend deixou de calcular notas TRI por fórmula fixa. Exibe somente exames devolvidos pela API, envia alternativas por posição, solicita o cálculo no backend e lê resultados persistidos por ID.
- O histórico lê tentativas e redações da API. Estados sem dados e falhas são explícitos.
- A redação digitada é persistida e enviada ao avaliador configurado. A resposta precisa ter cinco competências distintas, níveis válidos, soma consistente e evidências literais presentes no texto. Falhas do provedor retornam 503; respostas inválidas retornam 502. Nenhuma nota de contingência é gerada.
- Rotas administrativas que simulavam uma importação ou publicavam métricas e transformação de escala fixas agora rejeitam essas operações.
- O downloader preserva arquivo parcial, retoma por HTTP Range quando disponível e exige SHA-256 verificado antes de liberar o arquivo. O manifesto de 2025 registra o pacote oficial efetivamente baixado e validado.
- Questões anuladas são excluídas do padrão psicométrico; não recebem acerto arbitrário. A API pública de caderno não expõe o gabarito.

## Dados oficiais auditados nesta etapa

O [Inep disponibiliza os microdados do ENEM 2025](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem) e o [gabarito oficial do segundo dia](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/2025). O pacote baixado tem 1.035.674.693 bytes; o SHA-256 auditado e a data de modificação da fonte constam em `pipelines/inep/manifests/2025.yaml`. O arquivo passou no teste de integridade do 7-Zip. A tabela `ITENS_PROVA_2025.csv` traz parâmetros `a`, `b`, `c` publicados pelo Inep, não estimados pelo produto.

O comando `python -m pipelines.inep.import_2025` cruza cada posição da tabela de itens com o PDF do gabarito oficial e identifica de forma única os códigos de prova 1484 (Natureza) e 1472 (Matemática), ambos do caderno amarelo regular do segundo dia. A saída auditável fica em `data/processed/2025/itens_d2_caderno5_amarelo.json`, fora do controle de versão. São 90 posições: 3 anuladas no gabarito e mais 2 com alternativa divulgada, mas excluídas da análise psicométrica no microdado. Há parâmetros publicados para 85 itens. O script de cobertura `python -m pipelines.inep.audit_results_2025` lê os resultados Deflate64 em fluxo e grava apenas contagens agregadas, sem identificadores ou respostas individuais. Foram verificados 794.416 registros presentes em cada área para esses códigos; todas as sequências de respostas e gabaritos tinham 45 posições e coincidiam com o caderno identificado.

O comando `python -m pipelines.inep.import_regular_2025` valida os oito gabaritos impressos da [aplicação regular de 2025](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/2025) contra as 185 identidades distintas de itens da tabela oficial. O primeiro dia mantém as cinco posições de inglês e as cinco de espanhol separadas. O mapeamento fica em `data/processed/2025/cadernos_regulares.json`.

O comando `python -m pipelines.inep.validate_official_2025` comparou estimativas EAP e notas oficiais em uma amostra determinística de 1% dos resultados. Os parâmetros dos itens já vêm da tabela publicada pelo Inep; 70% da amostra foram reservados, 15% usados para ajustar a transformação de escala e 15% mantidos para avaliar a transformação. O holdout **não é independente da calibração original dos itens feita pelo Inep**, mas não foi usado para ajustar a escala deste produto. Registros com 45 respostas em branco e nota oficial zero foram identificados separadamente e excluídos da comparação de proficiência.

| Área | Casos no holdout | MAE | Correlação |
| --- | ---: | ---: | ---: |
| Linguagens | 5.108 | 0,03 | 1,0000 |
| Humanas | 5.103 | 0,03 | 1,0000 |
| Natureza | 4.836 | 0,03 | 1,0000 |
| Matemática | 4.835 | 0,03 | 1,0000 |

O relatório completo, inclusive erros nas caudas e contagens de provas em branco, fica em `data/processed/2025/validacao_notas_regulares.json`. Os coeficientes de escala foram ajustados a partir dos dados, jamais fixados em 500 + 100θ. O script `python -m pipelines.inep.publish_regular_2025` criou backup e publicou no banco local 12 opções de caderno, 185 itens e quatro versões de calibração estimada. A antiga calibração fictícia continua marcada como `DEPRECATED`. A API sempre retorna `official: false` com aviso obrigatório; o simulador oferece o link do PDF da prova oficial correspondente.

Os 114 PDFs adicionados pelo usuário, de 2009 a 2024, foram catalogados por `python -m pipelines.inep.catalog_local_pdfs`. O inventário registra caminho, ano, aplicação, tamanho e hash em `data/processed/catalogo_provas_locais.json`. Quatro grupos de reaplicação de 2010–2011 não contêm gabarito na pasta.

Para 2024, o pacote de [microdados oficiais do Inep](https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/microdados/enem) foi baixado, verificado por SHA-256 e testado quanto à integridade. Os PDFs locais do primeiro dia azul e do segundo dia azul coincidem byte a byte com os gabaritos da [página oficial de provas de 2024](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos/2024). O comando `python -m pipelines.inep.import_selected_2024` cruzou esses dois cadernos com os itens oficiais, incluindo as cinco posições distintas de inglês e espanhol. Há 185 identidades de itens e uma questão anulada em Natureza.

O comando `python -m pipelines.inep.validate_selected_2024` aplicou o mesmo protocolo de 2025 a uma amostra determinística de 2%. Os casos de holdout não foram usados para ajustar a escala do produto, mas os parâmetros dos itens já tinham sido estimados pelo Inep a partir de dados da edição. A comparação excluiu provas inteiramente em branco com nota oficial zero.

| Área de 2024 | Casos no holdout | MAE | Correlação |
| --- | ---: | ---: | ---: |
| Linguagens | 2.376 | 0,03 | 1,0000 |
| Humanas | 2.375 | 0,03 | 1,0000 |
| Natureza | 2.244 | 0,03 | 1,0000 |
| Matemática | 2.245 | 0,03 | 1,0000 |

O relatório agregado está em `data/processed/2024/validacao_notas_selecionadas.json`. A maior diferença isolada em Matemática foi 5,91 pontos; nenhuma área teve erro superior a 35 pontos. O comando `python -m pipelines.inep.publish_selected_2024` fez backup e publicou no banco local **somente os dois cadernos físicos disponíveis**: primeiro dia azul, com opções inglês e espanhol, e segundo dia azul. As três opções do simulador apresentam o PDF oficial e notas estimadas com `official: false`. O recibo está em `data/processed/2024/publicacao_banco_local.json`.

O banco SQLite local continha um exame 2025 de seed antigo e uma calibração publicada com hash SHA-256 do conjunto vazio. Foi criado backup em `data/processed/local-db-backup-before-inep-2025.db`, o exame foi desativado e a calibração marcada como `DEPRECATED`. Rotas de caderno, nova tentativa e cálculo recusam exame inativo.

Os enunciados de 2024 e 2025 não foram copiados para o banco; o aluno consulta o PDF oficial no simulador. As outras cores de 2024, os cadernos de atendimento especializado, as reaplicações e os anos de 2009 a 2023 continuam fora da API.

## Limites científicos e operacionais

Os testes unitários psicométricos usam simulações para verificar a matemática. As validações reais de 2024 e 2025 medem o ajuste de escala sobre resultados das próprias edições usadas pelo Inep para divulgar os parâmetros de itens; por isso não demonstram generalização para outra edição nem autorizam chamar a nota de oficial. A rubrica de redação precisa ser versionada contra o conteúdo integral da [Cartilha 2026](https://www.gov.br/inep/pt-br/centrais-de-conteudo/acervo-linha-editorial/publicacoes-institucionais/avaliacoes-e-exames-da-educacao-basica/a-redacao-do-enem-2026-cartilha-do-a-participante); o prompt atual é uma pré-avaliação pedagógica, sem validação contra corretores humanos.

## Próximo fluxo vertical

1. Ampliar a cobertura de 2024 às outras cores e a cobertura histórica de 2009 a 2023 com microdados oficiais de cada edição; localizar gabaritos faltantes das reaplicações. Os PDFs antigos já estão inventariados.
2. Revisar eventual incorporação de enunciados ao produto, preservando figuras e direitos aplicáveis; o fluxo atual usa os PDFs oficiais externos.
3. Integrar OCR com confirmação de transcrição e construir avaliação humana operacional.
