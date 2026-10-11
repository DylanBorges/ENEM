# Arquitetura do ENEM Intelligence

## Visão Geral

O **ENEM Intelligence** é uma plataforma distribuída para processamento psicométrico e diagnóstico pedagógico de simulados do ENEM.

```
                      +-----------------------------+
                      |   Frontend (Next.js 15)     |
                      |  Web Responsiva / UI Aluno  |
                      +--------------+--------------+
                                     | REST / JSON
                                     v
                      +-----------------------------+
                      |    Backend API (FastAPI)    |
                      |  Auth, RBAC, Multi-tenancy  |
                      +-------+--------------+------+
                              |              |
                +-------------+              +-------------+
                v                                          v
      +-------------------+                      +-------------------+
      | PostgreSQL (16)   |                      | Redis 7 (Broker)  |
      | 25 Tabelas / UUID |                      +---------+---------+
      +-------------------+                                |
                                                           v
                                                 +-------------------+
                                                 | Celery Worker     |
                                                 | OMR, PDF, ML      |
                                                 +---------+---------+
                                                           |
                                                           v
                                                 +-------------------+
                                                 | tri_core (Puro)   |
                                                 | 3PL + EAP / MML   |
                                                 +-------------------+
```

## Princípios Arquiteturais

1. **Núcleo Psicométrico Puro (`packages/tri_core`)**:
   Totalmente isolado. Não importa FastAPI, SQLAlchemy, Redis ou Celery. Matemática determinística, vetorizada em NumPy/SciPy e auditável.

2. **Multi-tenancy Rigoroso**:
   Controle RBAC em todas as rotas institucionais. Nenhuma escola ou gestor tem visibilidade sobre turmas ou estudantes de outra instituição.

3. **Privacy by Design & LGPD**:
   Fotos de cartões de resposta possuem TTL de expiração automática (24h). Dados sensíveis não são gravados em logs estruturados.
