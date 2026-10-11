# Documentação da API REST

A API do ENEM Intelligence é estruturada em rotas tipadas com OpenAPI (Swagger) disponível em `/docs`.

## Principais Endpoints

### Autenticação
- `POST /v1/auth/register`: Registro de usuário
- `POST /v1/auth/login`: Autenticação e emissão de JWT
- `POST /v1/auth/refresh`: Renovação de token de acesso
- `POST /v1/auth/logout`: Encerramento de sessão
- `GET /v1/auth/me`: Perfil do usuário atual

### Exames e Cadernos
- `GET /v1/exams`: Lista exames cadastrados
- `GET /v1/exams/{id}/booklets`: Lista cadernos de prova
- `GET /v1/exams/booklets/{id}/items`: Lista itens do caderno com gabarito oficial

### Simulados e Scoring
- `POST /v1/attempts`: Inicia uma tentativa
- `GET /v1/attempts/{id}`: Detalhes da tentativa
- `PUT /v1/attempts/{id}/responses`: Salva respostas (manuais ou OMR)
- `POST /v1/attempts/{id}/answer-sheet`: Upload de foto do cartão-resposta (OMR)
- `POST /v1/attempts/{id}/score`: Dispara cálculo de nota TRI (3PL + EAP)
- `GET /v1/attempts/{id}/score`: Consulta nota estimada persistida

### Redação
- `POST /v1/essays`: Envia proposta de redação
- `POST /v1/essays/{id}/pregrade`: Pré-avaliação IA nas 5 competências oficiais
- `POST /v1/essays/{id}/human-review`: Solicita dupla correção humana

### Instituições (B2B)
- `GET /v1/institutions/{id}/dashboard`: Painel institucional com isolamento multi-tenant
- `GET /v1/institutions/{id}/cohorts`: Turmas da instituição
