# Diretrizes para Agentes e Engenheiros de IA (AGENTS.md)

Este documento define regras inegociáveis para qualquer agente ou engenheiro trabalhando no repositório **ENEM Intelligence**.

## 1. Integridade Psicométrica
- **NUNCA invente ou hardcode parâmetros $a, b, c$ do ENEM.**
- **NUNCA invente transformações lineares arbitrárias como $500 + 100\theta$ apresentando-as como oficiais.**
- O pacote `packages/tri_core` é uma biblioteca matemática pura:
  - **PROIBIDO** importar FastAPI, SQLAlchemy, PostgreSQL, Redis ou Celery dentro de `tri_core`.
- Toda nota calculada DEVE carregar o atributo `official: false` e disclaimer obrigatório.
- Se não houver calibração para uma prova, a API deve falhar explicitamente com erro 422, jamais fabricar parâmetros silenciosamente.

## 2. Multi-tenancy & Segurança
- Todas as consultas institucionais devem ser blindadas por `check_institution_access`.
- Testes negativos de multi-tenancy devem ser mantidos e expandidos sempre que novas rotas forem adicionadas.
- Nenhuma instituição pode acessar registros de outra.

## 3. Privacidade e LGPD
- Imagens de cartão-resposta devem ter TTL de 24 horas no modelo `Upload`.
- Senhas, tokens e textos integrais de redação NUNCA devem ser registrados em logs estruturados.

## 4. Portabilidade e Testabilidade
- O sistema deve rodar tanto via `docker compose up --build` quanto localmente via SQLite/PostgreSQL.
- Ao realizar alterações, execute a suíte de testes com:
  ```bash
  pytest packages/tri_core/tests services/api/tests services/worker/tests pipelines/inep/tests -v
  ```
- Nenhuma etapa deve ser dada como concluída com testes falhando.
