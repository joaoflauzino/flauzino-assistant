# Reavaliação da Organização dos Services — Navegabilidade e Domínios

> **Status:** proposta para revisão humana; nenhuma movimentação de código foi feita.
> **Base:** estado do repositório em `dc3246e` (`feat/refactor`), após o split de `protocols.py`.
> **Escopo:** `finance_api/services/` e `agent_api/services/`.
> **Relação com o diagnóstico anterior:** esta reavaliação complementa o retrato histórico de [01](./01-diagnostico-inventario-e-decisoes.md); não o reescreve.

---

## 1. Pergunta reavaliada

O diagnóstico anterior respondeu principalmente se os agrupamentos atingiam o limiar estrutural da Regra 8. Esta reavaliação prioriza outra pergunta:

> **Para tarefas comuns de manutenção, que arquivos um desenvolvedor espera encontrar juntos e que estrutura reduz a navegação pela raiz de `services/` sem esconder dependências ou responsabilidades distintas?**

O número de arquivos e LOC continua sendo evidência, mas não substitui a avaliação da fronteira semântica. Uma pasta pequena não é automaticamente melhor; estar abaixo do limiar também não encerra a análise de navegação.

## 2. Retrato atual

| Diretório | Módulos na raiz | LOC aproximadas na raiz | Pacotes de feature existentes |
|---|---:|---:|---|
| `finance_api/services/` | 25 | 2.571 | `imports/` (15 módulos, incluindo `protocols.py`) |
| `agent_api/services/` | 11 | 1.206 | `tools/` (7 módulos) |

O estado atual já inclui `ai_classifier_protocols.py`, `classification_protocols.py`, `lookup_protocols.py` e `update_preparation_protocols.py`. Portanto, o número de arquivos na raiz de `finance_api/services/` aumentou após o split do bag de contratos. A separação melhorou a coesão dos contratos, mas não reduziu a carga de navegação da raiz.

## 3. Critérios usados nesta reavaliação

Um agrupamento é forte quando:

1. há uma tarefa de manutenção identificável que leva naturalmente a esses módulos;
2. existe dependência ou vocabulário de domínio compartilhado, e os consumidores entendem a fronteira;
3. a pasta não mistura CRUDs independentes só porque compartilham palavras;
4. os imports ficam mais explicativos, sem criar reexports ou uma camada de composição artificial;
5. o ganho de navegação compensa o custo de atualizar imports, testes e patch targets.

O gate atual continua sendo um detector estrutural, não uma medição direta de discoverability. Qualquer exceção semântica recorrente deve ser registrada na política de organização antes de virar padrão para novos pacotes.

## 4. Decisões por agrupamento

### F1 — Classificação financeira, incluindo o cliente de IA

**Módulos relacionados hoje:**

- `classification.py` — fachada/orquestrador, 139 LOC;
- `classification_chain.py` — handlers e construção da cadeia, 248 LOC;
- `extractors.py` — pipeline de extração, 104 LOC;
- `classification_protocols.py` — contratos da cadeia e extração, 25 LOC;
- `ai_classifier.py` — cliente HTTP e helpers de payload/resposta, 99 LOC;
- `ai_classifier_protocols.py` — contrato HTTP do cliente, 17 LOC.

**Evidência de coesão:** `classification.py` compõe a cadeia e o pipeline de extração e cria `AIClassifierClient`. O cliente de IA também é consumido por `services/imports/{enrichment,factory,wiring}.py`; portanto, ele não é apenas um detalhe privado da chamada feita pelo `ClassificationService`, mas ainda pertence à capacidade de classificação de transações. Os protocolos desses módulos são contratos dessa capacidade, não contratos transversais.

**Recomendação:** agrupar a capacidade em um pacote plano `finance_api/services/classification/`. A proposta de arquivos é:

```text
services/classification/
├── __init__.py       # vazio
├── service.py        # antigo classification.py
├── chain.py          # antigo classification_chain.py
├── extractors.py
├── ai_classifier.py
├── protocols.py      # antigo classification_protocols.py
└── ai_client_protocols.py  # antigo ai_classifier_protocols.py
```

Isso coloca `ai_classifier` e seu protocolo no mesmo domínio, sem criar um pacote de dois arquivos só para o cliente. O pacote teria seis módulos de produção e aproximadamente 632 LOC. Os protocolos continuam separados das implementações; os contratos da cadeia/extração ficam em `protocols.py`, e o contrato HTTP em `ai_client_protocols.py`. A proposta preserva a separação por movimentação/renomeação dos módulos, sem exigir a fusão de arquivos. Os consumidores de `AIClassifierClient` em `imports/` continuariam importando diretamente do módulo do cliente.

**Custo/risco:** mudar imports de DI, router de imports, serviços de importação, testes e alvos de patch que referenciam os módulos atuais. A migração não deve manter aliases nos caminhos antigos.

**Confiança:** alta. É o melhor exemplo de agrupamento que reduz a dispersão sem juntar responsabilidades CRUD independentes.

### A1 — Clientes HTTP do `agent_api`

**Módulos relacionados:** `base.py` (10 LOC), `finance.py` (262 LOC) e `graph.py` (41 LOC), aproximadamente 313 LOC.

**Evidência de coesão:** `FinanceService` e `GraphService` herdam de `BaseHttpService`; ambos são adapters HTTP para APIs downstream. São injetados na composição do agente e consumidos pelas tools. A relação é estrutural e explícita no código, não apenas nominal.

**Recomendação:** agrupar em `agent_api/services/clients/`:

```text
services/clients/
├── __init__.py  # vazio
├── base.py
├── finance.py
└── graph.py
```

**Custo/risco:** atualizar `dependencies.py`, `agent.py`, `tools/*`, testes de serviços/tools e patch targets que usem os caminhos antigos. A direção permanece `conversation/agent → clients` e `tools → clients`, sem necessidade de os clients importarem tools.

**Confiança:** alta. É uma fronteira de integração concreta e já tem uma classe-base comum.

### A2 — Fluxo de conversa do `agent_api`

**Módulos relacionados:** `agent.py` (194 LOC), `chat.py` (113 LOC) e `system_prompt.py` (178 LOC), aproximadamente 485 LOC.

**Evidência de coesão:** o fluxo é `ChatService → AgentService → system prompt`, e `AgentService` compõe clients e tools. Para uma tarefa como “alterar o comportamento de conversa”, esses arquivos são encontrados juntos.

**Contraponto:** `chat.py` também é responsável por persistência e sessão; `system_prompt.py` tem uma razão de mudança própria (instruções do LLM); `agent.py` contém o runtime LangChain. A pasta representa uma feature/workflow, mas não uma única razão de mudança.

**Recomendação:** candidato válido a `agent_api/services/conversation/`, mas condicional à preferência explícita por navegação por feature. Se criado:

```text
services/conversation/
├── __init__.py  # vazio
├── agent.py
├── chat.py
└── system_prompt.py
```

**Custo/risco:** além de routers e DI, há patch targets conhecidos em `agent_api.services.agent.create_agent` (13 usos reportados no inventário anterior). Eles precisam ser atualizados no mesmo movimento.

**Confiança:** média. O fluxo é claro, mas o agrupamento junta persistência, runtime LLM e prompt. Deve ser comparado com a árvore atual antes de aprovar.

### F2 — Pipeline de classificação versus processamento de mídia no `agent_api`

- `classify.py` (144 LOC) é o serviço da rota de classificação em lote; não deve ser agrupado automaticamente com `finance_api` só por usar a palavra “classify”. São APIs e responsabilidades distintas.
- `audio.py` (60 LOC) e `ocr.py` (108 LOC) são adapters de engines diferentes, com erros, dependências e routers próprios. Ambos lidam com entrada de mídia, mas hoje não compartilham pipeline nem composição.

**Recomendação:** manter `classify.py`, `audio.py` e `ocr.py` na raiz por enquanto. `media/` é uma possibilidade se surgir uma jornada compartilhada de upload/processamento ou se as rotas passarem a ser mantidas como uma feature conjunta; o nome comum “mídia” sozinho não basta.

**Confiança:** alta para manter planos no estado atual.

### F3 — Resolução de pagamento versus cadastro de métodos

`payment_resolution.py` (75 LOC) e `payment_resolution_steps.py` (73 LOC) têm uma relação direta: o primeiro monta e executa os steps do segundo. A capacidade é usada por despesas, receitas e assinaturas. `payment_methods.py` (63 LOC), apesar do prefixo lexical compartilhado, é um CRUD independente.

**Recomendação:** manter `payment_methods.py` separado. Manter `payment_resolution.py` e `payment_resolution_steps.py` planos por ora: os nomes já formam um par localizável e mover apenas dois arquivos criaria uma pasta pequena com baixo ganho mensurado. Reavaliar se a capacidade ganhar novos módulos (por exemplo, políticas, contratos ou mais steps).

**Confiança:** alta para não criar `payments/`; média para manter resolução plana se a raiz continuar sendo reorganizada.

### F4 — Preparação de updates e protocolos de lookup

`update_preparation.py` (166 LOC) e `update_preparation_protocols.py` (32 LOC) formam um par claro. `lookup_protocols.py` (25 LOC), no entanto, também é consumido por `imports/bulk_strategies.py`; não pertence exclusivamente à preparação de updates.

**Recomendação:** por enquanto, manter os três módulos planos. Se surgir `update_preparation/`, deixar os protocolos de lookup compartilhados fora do pacote ou definir uma fronteira de domínio mais ampla; não mover `lookup_protocols.py` para lá enquanto `imports/` for consumidor direto.

**Confiança:** média. Há coesão local, mas a existência do consumidor cross-feature reduz a clareza de um pacote pequeno.

### F5 — CRUDs e serviços financeiros independentes

`accounts.py`, `categories.py`, `credit_cards.py`, `income_categories.py`, `limits.py`, `payment_methods.py`, `incomes.py`, `spents.py`, `subscriptions.py`, `invoices.py` e `balances.py` têm consumidores e responsabilidades identificáveis por serviço/router. Agrupá-los em `entities/`, `crud/` ou em pastas por simetria de API criaria uma hierarquia de camada/entidade, não necessariamente uma fronteira de feature.

**Recomendação:** mantê-los na raiz, exceto quando uma relação de domínio compartilhada demonstrar uma tarefa real de manutenção conjunta. `imports/` continua sendo o precedente de pacote de feature, não um molde para colocar todo service em uma pasta.

## 5. Árvore comparada — proposta preferida

Esta é uma hipótese de navegação, não autorização para implementação:

```text
finance_api/services/
├── classification/          # pacote proposto (F1)
├── imports/                 # existente
├── accounts.py
├── balances.py
├── categories.py
├── credit_cards.py
├── dashboard_strategies.py
├── income_categories.py
├── incomes.py
├── invoices.py
├── limits.py
├── lookup_protocols.py
├── payment_methods.py
├── payment_resolution.py
├── payment_resolution_steps.py
├── protocols.py
├── spents.py
├── subscriptions.py
├── update_preparation.py
├── update_preparation_protocols.py
└── utils.py

agent_api/services/
├── clients/                 # pacote proposto (A1)
├── conversation/            # candidato condicional (A2)
├── tools/                   # existente
├── audio.py                 # manter plano
├── classify.py              # manter plano
├── ocr.py                   # manter plano
├── protocols.py
└── utils.py
```

Comparada à raiz atual, a proposta F1 + A1 agrupa primeiro as fronteiras com evidência mais forte. A2 é uma escolha de navegação por feature e deve ser aprovada separadamente; não é pré-requisito para F1/A1.

## 6. Implicações para a política

1. Manter o limiar atual como gatilho objetivo do gate, sem usá-lo como único critério de discoverability.
2. Acrescentar à documentação uma exceção explícita e revisável para pacotes semânticos menores, condicionada às evidências de coesão e navegação deste diagnóstico. Isso evita que o gate de tamanho seja interpretado como proibição absoluta abaixo do limiar.
3. Não criar regra automática de “pasta para todo par `módulo + protocol`”. O par `ai_classifier` é recomendado como parte do pacote maior de classificação, não como pacote isolado de dois arquivos.
4. Não aprovar `conversation/` no mesmo lote por simetria; decidir depois de comparar o benefício de agrupar o workflow com o custo de misturar persistência e runtime LLM.

## 7. Riscos e salvaguardas para eventual implementação

- Mover um módulo altera os caminhos usados por routers, DI, serviços de outras features, testes e monkeypatches. A migração deve atualizar todos no mesmo escopo.
- `conversation/agent.py` exige atenção especial aos patches de `create_agent`.
- Não deixar módulos antigos como aliases/reexports; cada símbolo deve ter uma fonte de import.
- Manter `__init__.py` vazio e módulos internos flat, sem subpacotes `handlers/` ou `strategies/`.
- Fazer F1 e A1 como unidades independentes; A2 exige aprovação própria.
- Antes de qualquer implementação, registrar a decisão humana e atualizar a documentação normativa se a exceção para pacotes abaixo do limiar for aceita.

## 8. Decisão humana pendente

| Opção | Decisão |
|---|---|
| **A — recomendada** | **Aprovada pelo desenvolvedor** (“Gostei! Segue implementação!”): implementar F1 + A1; avaliar A2 separadamente. A documentação normativa será atualizada antes das movimentações. |
| B | Aprovar somente F1, mantendo adapters do `agent_api` planos. |
| C | Manter os serviços planos e encerrar a reavaliação sem implementação. |
| D | Solicitar outro agrupamento ou justificar uma árvore diferente antes de abrir a implementação. |

`conversation/` (A2) não está incluído na aprovação. Nenhum arquivo Python foi movido ou alterado por esta reavaliação.
