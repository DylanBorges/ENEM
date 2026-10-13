# ENEM Intelligence

> Plataforma independente de inteligência de desempenho e estimativa psicométrica de notas do ENEM baseada em Teoria de Resposta ao Item (TRI) e Inteligência Artificial.

---

### Aviso Legal Obrigatório
**Este software NÃO é um produto oficial e NÃO é filiado ao INEP ou ao Ministério da Educação (MEC).**
Todas as notas geradas pela plataforma são **estimativas independentes** produzidas a partir de calibrações empíricas com microdados históricos públicos do exame. A metodologia considera os padrões de resposta e características dos itens sob o modelo logístico 3PL e estimador Bayesiano EAP, mas não substitui a divulgação oficial do INEP.

---

## 🏛️ Arquitetura do Repositório

Monorepo estruturado com separação estrita de responsabilidades:

```text
enem-intelligence/
├── AGENTS.md                   # Diretrizes inegociáveis para agentes e engenheiros de IA
├── README.md                   # Este guia de instalação e execução
├── .env.example                # Variáveis de ambiente de referência
├── Makefile                    # Automação de comandos (up, down, test, migrate)
├── docker-compose.yml          # Orquestração (web, api, worker, postgres, redis)
├── apps/
│   └── web/                    # Frontend Next.js 15 + TypeScript + Tailwind
├── services/
│   ├── api/                    # Backend FastAPI + SQLAlchemy (25 tabelas / RBAC / Multi-tenancy)
│   └── worker/                 # Celery Worker (OMR por visão computacional, PDFs e tarefas assíncronas)
├── packages/
│   └── tri_core/               # Núcleo psicométrico PURO (3PL, EAP, MML/EM, Linking, Validação)
├── pipelines/
│   └── inep/                   # Ingestão reproduzível, schemas por edição, calibração e release gates
└── docs/                       # Documentação técnica e metodológica detalhada
```

---

## 🚀 Como Iniciar

### 1. Pré-requisitos
- **Docker** e **Docker Compose** (ou Python 3.10+ e Node.js 18+)

### 2. Configuração de Variáveis de Ambiente
Copie o arquivo de exemplo:
```bash
cp .env.example .env
```

Para ativar a pré-avaliação de redação sem cobrança, crie uma chave em
[Google AI Studio](https://aistudio.google.com/api-keys) em um projeto no plano
**Free** e preencha `GEMINI_API_KEY` no `.env` da raiz. O modelo padrão é
`gemini-3.8-flash`. Não ative faturamento no projeto se quiser limitar o uso à
cota gratuita; ao esgotá-la, a avaliação poderá ficar indisponível. Reinicie a
API depois de alterar o `.env`. O Docker Compose repassa a chave à API; na
execução local, a API lê esse mesmo arquivo da raiz do repositório.

Os termos do plano gratuito permitem que o provedor use entradas e saídas para
melhorar seus serviços. Use somente redações sem dados pessoais nesse plano e
informe essa condição aos estudantes antes de enviar textos ao provedor.

### 3. Execução Completa via Docker Compose
Para subir o banco PostgreSQL, Redis, API FastAPI, Celery Worker e Frontend Next.js:
```bash
docker compose up --build
```

Acesse:
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **API Swagger / Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Checks**: [http://localhost:8000/health/live](http://localhost:8000/health/live) e [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

---

## 📚 Banco de questões no site

O catálogo TRI mostra apenas itens com calibração publicada. O enunciado, as
figuras e as cinco alternativas são servidos separadamente pela API, sem
renderizar páginas de PDF. O arquivo versionado
`services/api/app/db/question_content.json` e as imagens em
`apps/web/public/question-images/` permitem usar o site sem os PDFs locais.

A transcrição de 2017–2023 veio do acervo [enem.dev](https://github.com/ardotheedu/api-enem),
com correspondência textual ao caderno local e gabarito da transcrição;
2024–2025 usam os textos acessíveis DOSVOX,
os cadernos e os gabaritos oficiais do
[Inep](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos).
Quando a correspondência entre cadernos ou uma alternativa é incerta, o item
permanece no catálogo, mas a leitura e a resposta no site ficam indisponíveis.
As disciplinas específicas são sugestões automáticas baseadas no texto e
podem ficar vazias em questões ambíguas; os microdados só identificam a área.

Para regenerar os arquivos, instale `pipelines/inep/requirements.txt`, tenha
o banco SQLite de referência, os cadernos e gabaritos oficiais em
`data/booklets/` e os JSONs do enem.dev em `data/processed/enem-dev/quiz-items/`.
Depois execute `python -m pipelines.inep.build_question_content` na raiz.
Os diretórios de entrada não são enviados no deploy.

---

## 🧪 Testes Automatizados

O repositório possui uma suíte inicial de testes unitários e de integração. Ela ainda não cobre todos os critérios de aceite do projeto:

```bash
# Executa todos os testes do monorepo:
pytest packages/tri_core/tests services/api/tests services/worker/tests pipelines/inep/tests -v

# Ou separadamente:
pytest packages/tri_core/tests -v   # 15 testes matemáticos e psicométricos
pytest services/api/tests -v          # 7 testes de autenticação, scoring e multi-tenant
pytest services/worker/tests -v       # 2 testes de OMR sintético e PDF
pytest pipelines/inep/tests -v        # 2 testes de ingestão de microdados e calibração
```

---

## 🗄️ Banco de Dados e Migrações (Alembic)

O banco é modelado com 25 tabelas relacionais em UUID e compatibilidade total com PostgreSQL e SQLite.

Para aplicar migrações manualmente:
```bash
cd services/api
alembic upgrade head
```

---

## 📊 Pipeline de Microdados e Calibração TRI

1. **Manifestos e Schemas**:
   Cada edição oficial do ENEM é mapeada em `pipelines/inep/manifests/YYYY.yaml` e `pipelines/inep/schemas/YYYY.yaml`.
2. **Download e Verificação**:
   O download valida o hash criptográfico SHA-256 antes da ingestão.
3. **Divisão Anti-Leakage**:
   - 70% Calibração dos itens (algoritmo Marginal Maximum Likelihood / EM);
   - 15% Linking empírico da escala ($\alpha$ e $\beta$);
   - 15% Holdout intocado para avaliação de erro (MAE, RMSE, bias e decil).
4. **Release Gate**:
   Uma versão só é marcada como `PUBLISHED` se MAE e correlação cumprirem os limiares de qualidade no holdout.

---

## 🛡️ Privacidade e LGPD

- Fotos de cartões enviadas para OMR recebem expiração com TTL de 24 horas no modelo `Upload`.
- Dados sensíveis, senhas e textos integrais de redações nunca são impressos em logs de execução.
- Isolamento multi-tenant restrito: a Instituição A jamais tem acesso aos dados da Instituição B.

---

## ⚠️ Limitações Conhecidas

- **OMR Orientado a Template**: Fotos com desvios extremos de iluminação ou curvatura severa acionam o status `requires_confirmation`, solicitando que o usuário confirme manualmente as alternativas ambíguas.
- **Cobertura de Itens**: Provas sem calibração publicada bloqueiam o cálculo da nota em vez de inventar parâmetros.
- **Dados oficiais**: Nenhuma edição histórica foi importada e validada de ponta a ponta neste repositório. O manifesto de 2025 aguarda hash verificado.
- **Redação**: A avaliação depende de `GEMINI_API_KEY` e do pacote `google-genai`. Sem provedor disponível ou com saída inválida, a API falha sem gerar nota.
- **Produção**: OCR de redação, calibração com microdados oficiais, revisão humana operacional e importação administrativa persistente ainda precisam ser implementados.

Consulte [estado da implementação](docs/implementation-status.md) antes de usar notas ou dados para tomada de decisão.
