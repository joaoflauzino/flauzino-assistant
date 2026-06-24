# Projeto Flauzino Assistant - Diretrizes para o Gemini

Este documento serve como guia e explicação geral do projeto para a inteligência artificial (Gemini) e desenvolvedores atuando no repositório.

## Visão Geral do Projeto
O **Flauzino Assistant** é um assistente virtual criado para lidar com registros de gastos pessoais de forma inteligente e automatizada. O sistema possui uma arquitetura modularizada, compreendendo:
- **`infra/`**: Configurações de infraestrutura (Docker, banco de dados PostgreSQL).
- **`finance_api/`**: API principal (FastAPI) com a lógica de negócios e comunicação com o banco de dados.
- **`agent_api/`**: Interface de conversação via LLM que processa requisições do usuário e interage com a API financeira.
- **`telegram_api/`**: Bot do Telegram para interface do usuário, processando mensagens de texto e áudio/recibos.
- **`frontend/`**: Interface web moderna construída com React/Vite para gerenciamento visual e interativo dos gastos.

## Diretrizes Obrigatórias de Desenvolvimento

Ao atuar no desenvolvimento deste projeto, as seguintes regras são rigorosamente exigidas:

### 1. Testes Unitários
Toda nova feature ou modificação lógica precisa estar obrigatoriamente acompanhada de **testes unitários** utilizando a biblioteca `pytest`. Nenhuma feature deve ser considerada completa sem testes automatizados que validem o comportamento esperado.

### 2. Qualidade do Código (Linting e Formatação)
Após qualquer alteração no código, certifique-se de executar os seguintes comandos:
- `make format`: Para formatar o código automaticamente de acordo com as regras estabelecidas pelo `black`.
- `make lint`: Para garantir que não há erros ou violações de estilo (utilizando o `ruff`).

### 3. Padrões Python (PEP 8 e Zen of Python)
O projeto deve seguir continuamente as boas práticas do **Zen of Python** e as diretrizes de estilo do **PEP 8**. O código deve ser claro, explícito e legível.

**Regra Crítica para Imports:**
Jamais os imports podem ficar espalhados ou no meio do código! Todos os imports de bibliotecas, módulos ou pacotes locais devem ser organizados **exclusivamente no topo** de cada arquivo.

### 4. Arquitetura em Camadas
Todo projeto em Python neste repositório deve seguir rigorosamente a arquitetura em camadas com o fluxo: `route -> service -> repository`.
- **`route`**: Ponto de entrada das requisições. Recebe os dados, repassa para o service e devolve a resposta. Sem regra de negócio.
- **`service`**: Onde reside toda a lógica e regra de negócio.
- **`repository`**: Única camada responsável por acessar e persistir dados no banco.

### 5. Gerenciamento de Exceções
O tratamento de exceções não deve ter blocos `try/except` espalhados com tratamentos genéricos pelo código. Deve-se usar o padrão do projeto com **decorators** (como o decorator `@handle_service_errors` implementado em `finance_api.core.decorators`) nas funções da camada de serviço para capturar e tratar erros de banco de dados e exceções não previstas de forma centralizada e padronizada.

## Development Workflow

Para qualquer solicitação de nova feature:

1. Criar specs/<feature-name>.md
2. Analisar o código existente
3. Produzir especificação completa
4. Aguardar aprovação humana
5. Somente após aprovação iniciar implementação
6. Gerar plano de testes
7. Executar testes
