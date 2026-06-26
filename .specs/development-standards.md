# Establishing Project Development Standards

## Objetivo
Criar e formalizar diretrizes claras de desenvolvimento, padrões de codificação, e qualidade de código para o projeto Flauzino Assistant, documentando as regras para todos os desenvolvedores e para a Inteligência Artificial.

## Implementação
- Criação do arquivo `GEMINI.md` no root do projeto.
- Definição da obrigatoriedade de testes unitários com `pytest`.
- Inclusão das regras de formatação de código com `make format` (black) e `make lint` (ruff).
- Formalização dos padrões PEP 8 e Zen of Python, com regras específicas para imports de bibliotecas.
- Formalização do padrão de Arquitetura em Camadas (route -> service -> repository).
- Padronização no tratamento de exceções usando decorators como `@handle_service_errors`.

## Status
Implementado.
