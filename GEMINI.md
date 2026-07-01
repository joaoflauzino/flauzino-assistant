# Projeto Flauzino Assistant - Diretrizes para o Gemini / IAs

Este documento serve como guia e especificação oficial do projeto para qualquer inteligência artificial (Gemini, Cursor, Copilot, etc.) e desenvolvedores atuando no repositório. **Sempre leia e siga estas regras antes de sugerir código, escrever testes ou tomar decisões arquiteturais.**

## 1. Visão Geral do Projeto e Arquitetura
O **Flauzino Assistant** é um assistente virtual criado para lidar com registros de gastos pessoais de forma inteligente e automatizada. O sistema possui uma arquitetura modularizada:
- **`infra/`**: Configurações de infraestrutura (Docker Compose, banco de dados PostgreSQL).
- **`finance_api/`**: API principal (FastAPI) com a lógica de negócios e persistência. Usa o padrão Controller-Service-Repository.
- **`agent_api/`**: Interface de conversação via LLM. Utiliza `langchain` e modelos `gemini` para processar texto, áudio e imagens (OCR).
- **`telegram_api/`**: Bot do Telegram para interface do usuário, processando mensagens e comunicando-se com a `agent_api`.
- **`frontend/`**: Interface web moderna construída com React/Vite.

## 2. Tech Stack
- **Backend**: Python 3.13, FastAPI, Uvicorn
- **Banco de Dados**: PostgreSQL com `asyncpg`, SQLAlchemy 2.0 (Modo Async)
- **AI / LLM**: LangChain, Google GenAI (Gemini), Faster-Whisper (Áudio), PyTesseract (OCR)
- **Gerenciador de Pacotes**: `uv`
- **Testes**: `pytest`, `pytest-asyncio`, `pytest-mock`
- **Frontend**: React, Vite, Node.js 18+

## 3. Diretrizes Obrigatórias de Desenvolvimento Backend

### 3.1. Arquitetura em Camadas (Strict Separation of Concerns)
Todo projeto em Python neste repositório deve seguir rigorosamente a arquitetura em camadas com o fluxo: `route -> service -> repository`.
- **`routers/`**: Apenas lidam com requisições/respostas HTTP, validação de payload (via Pydantic) e delegação para os services. **Nunca** escreva regras de negócio ou consultas ao banco de dados aqui.
- **`services/`**: Onde reside toda a lógica e regra de negócio. Eles chamam os repositories para buscar/salvar dados.
- **`repositories/`**: Única camada responsável por acessar e persistir dados no banco. O único lugar onde consultas SQLAlchemy ORM (`select`, `insert`, `update`, `delete`) devem ser utilizadas.

### 3.2. Gerenciamento de Exceções Global
O tratamento de exceções não deve ter blocos `try/except` genéricos espalhados pelo código. 
- Use o padrão do projeto com **decorators** (como `@handle_service_errors` em `finance_api.core.decorators`) nas funções da camada de serviço.
- Sempre levante exceções customizadas (ex: `EntityNotFoundError`, `EntityConflictError` ou `DatabaseError`) definidas em `core/exceptions.py`.
- **NUNCA** retorne `HTTPException` diretamente dos Services ou Repositories. Deixe os global exception handlers no `main.py` formatarem a resposta centralizada.

### 3.3. Programação Assíncrona
- Sempre utilize `async` / `await` para operações de banco de dados, requisições HTTP (`httpx`) e operações de arquivos (I/O).
- O SQLAlchemy deve obrigatoriamente utilizar a sessão assíncrona (`AsyncSession`). Não faça chamadas síncronas ao banco.

### 3.4. Qualidade do Código e Padrões (PEP 8)
- **Regra Crítica para Imports:** Jamais os imports podem ficar espalhados ou no meio do código! Todos os imports de bibliotecas, módulos ou pacotes locais devem ser organizados **exclusivamente no topo** de cada arquivo.
- O código deve ser claro, com type hints (tipagem) **obrigatórios** para argumentos de funções e retornos.
- Após qualquer alteração, execute obrigatoriamente:
  - `make format`: Para formatar via `black`.
  - `make lint`: Para validação via `ruff`.

## 4. Testes Unitários
Toda nova feature ou modificação precisa estar acompanhada de **testes unitários** utilizando `pytest`. Nenhuma feature deve ser considerada completa sem testes.
- Posicione os testes no diretório `tests/` espelhando o caminho do módulo (ex: `tests/finance_api/routers/...`).
- O projeto usa `pytest-asyncio` em modo `auto`, atente-se às funções assíncronas.
- Utilize `pytest-mock` (`mocker`) para simular chamadas de banco de dados e APIs externas. **Não bata no banco de dados real** em testes unitários (a menos que explicitamente exigido para integração).

## 5. Gerenciamento de Dependências
- Utilize exclusivamente o `uv` para o gerenciamento de pacotes Python (`uv add <package>`, `uv sync`, `uv run`).
- **NUNCA** utilize `pip` diretamente.

## 6. Workflow de Desenvolvimento (Development Workflow)
Para qualquer solicitação de nova feature:
1. **Analisar**: Verificar se as alterações afetam a `finance_api`, `agent_api` e/ou `frontend`.
2. **Especificar**: Criar o arquivo de especificação `.specs/<feature-name>.md` e planejar Models -> Repositories -> Services -> Routers. Sempre salvar todos os detalhes de planejamento e detalhes de implementação técnica com exemplos de código e desenhos (formato mermaid) se necessário.
3. **Aprovação**: Aguardar a aprovação humana do plano de implementação/especificação.
4. **Implementar**: Somente após aprovação, iniciar a escrita do código respeitando os padrões descritos neste documento.
5. **Testar**: Gerar o plano de testes e escrever/executar os testes automatizados.
