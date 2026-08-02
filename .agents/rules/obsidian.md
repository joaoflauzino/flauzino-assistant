---
trigger: always_on
---

# Regra: Documentação Automática no Obsidian

Esta regra define o comportamento obrigatório da IA (Antigravity/Gemini) para manter a documentação do projeto sempre atualizada no Obsidian.
Abtes de qualquer passo, é necessário que a IA cheque se exite alguma pasta chamada "projetos". Caso não, ela deve criar. Dentro dessa pasta,
deve haver outra pasta com o nome do repositório. Caso não exista, ela deve criar. Após isso, ela deve criar ou atualizar (caso exista) essa
documentação de acordo com os passos abaixo.

## 1. Gatilho (Quando documentar)
A IA deve iniciar o processo de documentação no Obsidian sempre que:
- Uma nova feature for finalizada (conforme as `.specs/`).
- Uma refatoração importante ou mudança de arquitetura for concluída.
- Um plano de implementação (`implementation_plan.md`) for totalmente executado e validado.
- O usuário solicitar explicitamente ("atualize a documentação").
- Caso ficar na dúvida, pergunte se é necessário documentar no Obsidian.

## 2. Procedimento de Documentação (Fluxo de Autorização)
Ao identificar que uma atualização importante ocorreu, a IA **não deve terminar a conversa sem antes tratar a documentação**. Ela deve seguir estes passos:

1. **Elaborar o Resumo:** A IA deve criar um breve resumo (bullet points) do que planeja escrever nas notas do Obsidian e perguntar ao usuário: *"Posso prosseguir e registrar essas mudanças no Obsidian usando a skill?"*
2. **Uso da Skill:** Após a autorização do usuário, a IA deve invocar obrigatoriamente a skill do Obsidian (ex: `obsidian-cli`) para interagir com o Vault.
3. **Padrão de Qualidade:**
   - Atualizar notas existentes ou criar novas (como logs de decisão arquitetural - ADRs, ou specs técnicas).
   - Incluir contexto (o problema resolvido).
   - Incluir trechos de código relevantes, nomes de novos arquivos criados, e variáveis de ambiente (se houver).
   - Registrar links internos (wikilinks `[[Nota]]`) para conectar conceitos.
4. **ADRs (Architecture Decision Records):**
   - Toda decisão arquitetural ou refatoração importante deve gerar um ADR dentro da pasta `projetos/<nome-do-repo>/ADRs/`.
   - Nomenclatura sequencial: `ADR-001-Titulo-Descritivo.md`, `ADR-002-...`, etc.
   - Estrutura mínima do ADR: **Status**, **Data**, **Contexto** (o problema), **Decisão** (o que foi feito), **Consequências** (positivas e negativas), **Arquivos Criados/Modificados**.
   - Incluir wikilink para `[[Contexto_FlauzinoAssistant]]` no campo de contexto.
   - Referenciar o ADR no `README.md` do projeto no Obsidian (seção "Specs e ADRs").
5. **Confirmação:** Após executar a skill, avisar o usuário que a documentação foi salva com sucesso no cofre.

*(Nota para o usuário: Caso queira que a IA atue sem pedir permissão, basta alterar o passo 1 para: "A IA deve registrar as mudanças no Obsidian autonomamente, sem pedir autorização prévia, informando apenas quando concluir.")*

## 3. Gestão de Contexto e Memória (Diário de Bordo)

Para garantir a continuidade e evitar a perda de contexto entre diferentes interações ou sessões, a IA deve manter a documentação de contexto de desenvolvimento dentro da pasta `projetos/flauzino-assistant/contexto/` no Obsidian.
Cada dia de trabalho deve ter o seu próprio arquivo no formato `YYYY-MM-DD.md` (ex: `2026-08-01.md`). As informações devem ser acumuladas neste arquivo ao longo do dia.

### 3.1. Leitura Obrigatória (Recuperação de Contexto)
Sempre que uma nova conversa for iniciada e o usuário pedir para retomar o trabalho, ou quando a IA não tiver certeza do estado atual do projeto, a IA deve **obrigatoriamente ler o arquivo do dia atual (e os anteriores mais recentes se necessário) no Obsidian usando a skill** antes de planejar ou escrever qualquer código.

### 3.2. Estrutura e Atualização da Memória
Ao concluir uma feature importante, ou quando o usuário informar que a sessão/interação atual terminou, a IA deve atualizar o arquivo do dia no Obsidian contendo:
- **Resumo do que foi entregue:** (ex: "Criamos a integração com o Telegram").
- **Decisões e Padrões Importantes:** (ex: "Decidimos não usar banco de dados para os logs, apenas arquivos locais por enquanto").
- **Pontas Soltas / Próximos Passos (TODOs):** O que faltou fazer ou o que deve ser atacado na próxima iteração.
- **Desafios Enfrentados:** Algum bug persistente ou gambiarra temporária que precisará de revisão no futuro.

A IA deve tratar a pasta de contexto como o "cérebro compartilhado" entre ela e o usuário.