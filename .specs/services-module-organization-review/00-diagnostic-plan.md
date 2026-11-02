# Diagnóstico de Organização dos Services — `finance_api` e `agent_api`

> **Status:** 🟨 Proposta de diagnóstico — aguarda revisão/aprovação antes de qualquer reorganização
> **Execução:** fases 0–2 concluídas em 2026-11-02 → [01-diagnostico-inventario-e-decisoes.md](./01-diagnostico-inventario-e-decisoes.md). Decisão humana **A** registrada em §10.1 do relatório; implementação do C3 + Regra F especificada em [02-fase-implementacao-c3-protocols-split.md](./02-fase-implementacao-c3-protocols-split.md) e **aguardando aprovação**.
> **Escopo:** módulos de `finance_api/services/` e `agent_api/services/`
> **Motivação:** avaliar a percepção de desorganização e propor uma organização mais fácil de navegar, sem criar pacotes por estética ou alterar comportamento.
> **Contexto relacionado:** `.specs/services-modules-quality-refactoring/00-master-plan.md`, fases 3, 5 e 6.

---

## 1. Contexto e problema

A refatoração anterior agrupou o cluster de importação em `finance_api/services/imports/`, padronizou nomes e estabeleceu critérios de organização modular. Ainda assim, há muitos módulos no nível raiz de `finance_api/services/`, enquanto `agent_api/services/` contém responsabilidades de conversa, integração financeira/gráfica e processamento de mídia. A quantidade de arquivos no mesmo diretório pode dificultar a navegação, mas, por si só, não prova falta de coesão.

O critério atual recomenda um pacote plano de domínio quando um grupo no mesmo diretório compartilha prefixo/domínio, atinge pelo menos cinco módulos ou 800 LOC e tem dependências internas sem ciclos. Este diagnóstico deve avaliar se o critério responde ao problema percebido ou se agrupamentos semânticos e dependências reais justificam uma decisão diferente. Nenhum critério normativo será alterado nesta fase.

### Inventário inicial a confirmar

Os itens abaixo são hipóteses para investigação, não decisões de movimentação:

| API | Candidato | Pergunta de diagnóstico |
|---|---|---|
| `finance_api` | `classification.py`, `classification_chain.py`, `ai_classifier.py` e `extractors.py` | Formam um único domínio de classificação ou há responsabilidades/ciclos que recomendam mantê-los separados? O agrupamento semântico vai além do prefixo atual? |
| `finance_api` | `payment_methods.py`, `payment_resolution.py` e `payment_resolution_steps.py` | São partes de um mesmo domínio ou a resolução é uma dependência consumida por serviços de despesas, receitas e assinaturas, enquanto métodos de pagamento é uma feature distinta? |
| `finance_api` | `protocols.py` e `utils.py` | Os contratos e helpers estão coesos e têm consumidores claros ou misturam conceitos de vários serviços? |
| `agent_api` | `agent.py`, `chat.py` e `system_prompt.py` | Fazem parte de uma unidade de conversa com fronteiras claras ou devem permanecer como serviços independentes? |
| `agent_api` | `audio.py` e `ocr.py` | Há coesão suficiente para um domínio de mídia ou são adapters independentes expostos diretamente pelos routers? |
| `agent_api` | `finance.py`, `graph.py` e `tools/` | As ferramentas existentes estão agrupadas adequadamente e as dependências entre elas respeitam as fronteiras da API? |

`agent_api/services/tools/` e `finance_api/services/imports/` já são pacotes existentes; o diagnóstico deve tratá-los como referências e evitar duplicar a estrutura interna sem motivo comprovado.

---

## 2. Objetivos

1. Tornar mais clara a localização de um service pela sua responsabilidade de domínio.
2. Identificar módulos com coesão alta que poderiam formar pacotes planos e módulos que devem permanecer no nível atual.
3. Verificar se a organização atual de `protocols.py` e `utils.py` favorece ou prejudica a descoberta e o acoplamento.
4. Apresentar alternativas com custos, riscos e impactos em imports, DI, routers e testes.
5. Recomendar, se justificado, uma política complementar ao critério atual, sem enfraquecer o gate de arquitetura implicitamente.

## 3. Fora de escopo

- Mover ou renomear arquivos durante a fase de diagnóstico.
- Alterar lógica de negócio, assinaturas, contratos HTTP, prompt/docstrings de tools ou comportamento do LLM.
- Reorganizar `routers/`, `repositories/`, `schemas/`, `models/` ou outros diretórios das APIs.
- Reorganizar `telegram_api`, `graph_api`, `importers/` ou demais áreas não citadas.
- Criar uma hierarquia completa de pastas para espelhar entidades, endpoints ou camadas já existentes.
- Alterar a Regra 8 ou `tests/architecture/test_module_organization.py` antes de apresentar e aprovar uma justificativa.

---

## 4. Método de diagnóstico

### 4.1 Inventário

Para cada módulo de produção nos dois diretórios, registrar:

- caminho e LOC;
- responsabilidade principal, classes/funções públicas e dependências pesadas;
- consumidores de produção (routers, dependências, outros services e composição);
- consumidores de teste e alvos de monkeypatch por caminho de import;
- imports internos de service para service, com direção das dependências e possíveis ciclos;
- se o módulo implementa regra de negócio, integração externa, composição, contrato ou helper puro.

O inventário deve excluir `__pycache__`, testes e arquivos gerados. Os imports indiretos relevantes devem ser verificados no código, não inferidos somente pelo nome do arquivo.

### 4.2 Avaliação de coesão e limites

Para cada agrupamento candidato, responder explicitamente:

1. Os módulos mudam pelas mesmas razões de negócio?
2. Compartilham vocabulário e conceitos, ou apenas prefixo/imports?
3. Existe uma direção de dependência compreensível e sem ciclos?
4. O pacote teria um ponto de composição/entrada identificável, ou só esconderia arquivos numa pasta?
5. A localização melhoraria tarefas reais de navegação sem tornar imports e testes menos claros?

Não usar como justificativa suficiente o número de arquivos, o tamanho do diretório ou o desejo de simetria entre as duas APIs.

### 4.3 Alternativas

Para cada candidato, considerar e comparar:

- **Manter plano:** nenhum pacote novo; melhorar apenas documentação/nomenclatura caso necessário.
- **Pacote de domínio plano:** pacote com nomes de módulos sem repetir o nome do pacote, `__init__.py` interno sem reexports e sem subpacotes prematuros.
- **Separação local sem pacote:** dividir um módulo grande/coeso em poucos módulos flat quando isso resolver um problema específico.

Não propor compatibilidade por reexport de módulos antigos. Se a movimentação for recomendada numa fase posterior, os consumidores devem migrar para uma única fonte de import.

---

## 5. Entregáveis

1. Inventário de módulos e consumidores por API.
2. Mapa textual ou tabular das dependências internas relevantes, incluindo ciclos encontrados ou confirmando a ausência deles.
3. Matriz de decisão por candidato: evidências, opções consideradas, recomendação e justificativa.
4. Estruturas-alvo ilustrativas somente para candidatos aprovados pela análise; nenhuma delas é uma decisão de implementação nesta spec.
5. Lista de riscos e sequência sugerida para uma eventual fase de movimentação isolada.
6. Recomendação explícita sobre manter, complementar ou propor revisão do critério atual de criação de pacotes.

---

## 6. Critérios de aceite do diagnóstico

- [ ] Todos os módulos de produção em `finance_api/services/` e `agent_api/services/` aparecem no inventário ou têm exclusão justificada.
- [ ] Cada candidato do §1 tem uma decisão fundamentada, inclusive a possibilidade de mantê-lo plano.
- [ ] As dependências e consumidores relevantes foram verificados no código; ciclos potenciais foram registrados.
- [ ] Os impactos de imports usados por routers, DI, testes e monkeypatches estão descritos para cada movimentação sugerida.
- [ ] As recomendações preservam `route → service → repository` e os contratos públicos existentes.
- [ ] Nenhuma mudança de código ou de comportamento foi feita nesta fase.
- [ ] Qualquer proposta de alterar regra/gate está separada das recomendações estruturais e aguarda aprovação explícita.
- [ ] O resultado final é apresentado para revisão humana antes de abrir uma fase de implementação.

---

## 7. Fases sugeridas

| Fase | Escopo | Resultado |
|---|---|---|
| 0 | Confirmar inventário e consumidores dos dois diretórios | Mapa base validado |
| 1 | Avaliar coesão, dependências e limites por candidato | Matriz de decisão |
| 2 | Formular alternativas, riscos e recomendação de política | Proposta para revisão humana |
| 3 | Aguardar aprovação e, se solicitado, criar uma spec de implementação separada | Nenhuma movimentação automática nesta spec |

---

## 8. Salvaguardas para uma futura implementação

Se uma reorganização for aprovada em uma spec posterior:

- tratá-la como renomeação/movimentação pura, sem alteração de comportamento;
- fazer uma unidade de domínio por vez, mantendo o diff legível e verificável com `git diff -M`;
- atualizar imports de produção, testes, DI e patch targets no mesmo escopo da movimentação;
- manter `__init__.py` de pacotes internos sem `__all__` e sem reexports;
- atualizar caminhos dos testes para espelhar os módulos;
- verificar importação dos apps e executar os testes relevantes, além de `make format`, `make lint` e a suíte completa;
- apresentar o diff e o resumo ao desenvolvedor; não realizar commit ou push sem autorização explícita.
