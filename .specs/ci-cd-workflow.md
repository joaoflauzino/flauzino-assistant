# Professionalizing Development Workflow & CI/CD

## Objetivo
Profissionalizar o fluxo de trabalho de desenvolvimento com uma estratégia consistente de branchs (feature branches) e validação automatizada de qualidade.

## Implementação
- Padronização no uso de branches `feature/*`.
- Configuração de validação e CI/CD para rodar obrigatoriamente `black` (formatação) e `ruff` (linting).
- Restrição de branches para manter a `main` focada unicamente em deploy e infraestrutura via Docker.

## Status
Implementado.
