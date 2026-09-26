# Plano: Reestruturação do README

## Problema

O README.md atual está inflado com detalhes de setup, variáveis de ambiente, Docker, testes e formatação — tudo misturado. Ele não mostra **o que o Flauzino Assistant faz** de forma clara e rápida. Além disso:

- Referencia `mcp_server/` que não existe mais (agora é `graph_api/`)
- Usa `GEMINI_API_KEY` mas o Docker Compose já usa `OPENAI_API_KEY` e `gpt-6-luna`
- A seção de arquitetura é boa, mas se perde no meio de um mar de configuração

## Proposta

### README.md (Raiz) — Vitrine do Projeto

Foco: **O que é? Como funciona? Como rodo?**

Estrutura proposta:

1. **Título + Tagline** — Uma frase que vende o projeto
2. **O que é o Flauzino?** — 2-3 parágrafos explicando a proposta de valor
3. **Como funciona** — Diagrama Mermaid inline + explicação de cada módulo (1 linha por serviço)
4. **Quick Start** — Apenas `make install` → `.env` → `make docker-up` (3 passos)
5. **Tabela de serviços** — Link para README de cada serviço
6. **Desenvolvimento** — Comandos essenciais (`make test`, `make format`, `make lint`)

> Remover: toda a seção de variáveis detalhadas, Docker avançado, Tesseract, hooks, etc.
> Essas coisas vão para os READMEs dos serviços ou para um futuro `docs/CONTRIBUTING.md`.

### READMEs dos serviços (atualizar/criar)

| Serviço | Arquivo | Ação |
|:--|:--|:--|
| Finance API | `finance_api/README.md` | ✅ Já existe e está bom — manter |
| Agent API | `agent_api/README.md` | ✅ Já existe e está bom — manter |
| Graph API | `graph_api/README.md` | ⚠️ Placeholder — expandir |
| Telegram Bot | `telegram_api/README.md` | ⚠️ Desatualizado — reescrever |
| Frontend | `frontend/README.md` | ⚠️ Placeholder — expandir |
| Infra | `infra/README.md` | 🆕 Criar (Docker Compose, DB, variáveis de ambiente detalhadas) |

### Alterações no Mermaid

Atualizar o diagrama `docs/architecture.mmd` para refletir:

- `graph_api` ao invés de `mcp_server`
- Fluxo do Telegram (tanto o fluxo interativo `/gasto` direto pela Finance API, quanto áudio/foto pelo Agent)
- O gráfico agora é consumido pelo Telegram e pelo Finance API MCP tools

## Arquivos afetados

- `README.md` — Reescrita total
- `graph_api/README.md` — Expandir
- `telegram_api/README.md` — Reescrever
- `frontend/README.md` — Expandir
- `infra/README.md` — Criar novo
- `docs/architecture.mmd` — Atualizar

## O que NÃO muda

- `finance_api/README.md` — Já está detalhado e correto
- `agent_api/README.md` — Já está detalhado e correto
