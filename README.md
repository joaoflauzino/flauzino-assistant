# flauzino-assistant

Esse projeto tem como objetivo criar um assistente virtual capaz de lidar com registros de gastos pessoais de forma inteligente e automatizada.

## Roadmap

O desenvolvimento do projeto seguirá as seguintes etapas:

1.  **API de Gestão Financeira**
    -   Desenvolver uma API para registrar informações de gastos (*spents*) e limites de gastos (*spending limits*).
    -   Implementar a camada de repositório utilizando PostgreSQL ou outro banco de dados simples para persistência dos dados.

2.  **Ferramenta de Visualização e Gestão**
    -   Criar uma ferramenta para visualizar as informações de gastos.
    -   Permitir o cadastro manual de gastos e limites por categoria através desta interface.

3.  **Agente Inteligente de Extração**
    -   Desenvolver um agente capaz de interpretar frases em linguagem natural.
    -   Extrair informações de gastos ou limites definidos pelo usuário.
    -   Integrar com a API desenvolvida para registrar essas informações automaticamente.

## Como Executar (MVP - Agente Inteligente)

Atualmente, o projeto conta com uma implementação MVP do **Item 3 (Agente Inteligente de Extração)**. As demais funcionalidades (API e Visualização) estão em desenvolvimento.

Este projeto utiliza `uv` para gerenciamento de dependências.

1.  Instale as dependências:
    ```bash
    uv sync
    ```

2.  Configure a variável de ambiente `GEMINI_API_KEY`.

3.  Execute o assistente:
    ```bash
    uv run main.py
    ```
