# Relatório — Desenvolvimento do NossoBolso com agentes de código

**Projeto:** NossoBolso (Finanças Compartilhadas) — aplicação CRUD com cinco visões de usuário
**Equipe:** Heitor Gabriel Lucena Albuquerque, Victória Oliveira Estrela, Jamilly Melo Fernandes
**Disciplina:** Atividade 03 — Prof. Andrei Formiga — Julho de 2026

---

## 1. Como o desenvolvimento foi conduzido

O projeto foi construído com o **Claude Code** guiado por uma sequência de prompts planejada
antes de escrever qualquer código (`prompts-claude-code-financas-compartilhadas.md`). O fluxo de
trabalho em cada etapa foi:

1. Colar **um prompt por vez**, usando *plan mode* nos passos de arquitetura e permissões;
2. Revisar o diff gerado e **rodar o resultado** antes de aceitar;
3. Registrar no `DEVLOG.md` o que o agente acertou de primeira, onde errou e o que foi ajustado;
4. Commitar e só então avançar para o próximo prompt.

A fonte da verdade foi o plano da atividade versionado em `docs/plano.md`, que o agente leu no
prompt inicial para derivar `docs/arquitetura.md` e `docs/checklist.md`.

## 2. O que o agente acertou de primeira

- **Infraestrutura**: Docker Compose com healthcheck do PostgreSQL, Django + DRF conectados por
  variável de ambiente, endpoint de health — funcionou na primeira execução.
- **Modelo de dados**: os 12 modelos com constraints de unicidade e validações `clean()`,
  incluindo a decisão central do plano (papéis por **relacionamento**, não por tipo de usuário).
- **Frontend**: o scaffold Vite + Tailwind + Recharts com login, roteamento por papel e três
  painéis subiu sem nenhum ajuste manual.
- **Empacotamento**: Dockerfiles de produção (multi-stage no frontend) e o comando `seed_demo`.

## 3. Onde o agente errou — e como os testes pegaram

A lição mais importante do processo: **o código de permissões parecia correto na leitura, mas
os testes automatizados revelaram furos reais**. Bugs encontrados e corrigidos:

| Bug | Como foi pego |
|---|---|
| Qualquer membro podia editar/deletar o grupo (faltava travar escrita para o responsável) | Teste de permissão (Prompt 6) |
| Usuário A editava categoria de B se soubesse o ID | Teste de permissão |
| Admin ficava bloqueado de criar categorias padrão (a barreira `NaoAdmin` era ampla demais) | Teste de CRUD |
| Qualquer membro criava orçamento de grupo (faltava exigir gestor) | Teste de permissão |
| Dependente ainda via membros e o "quem deve a quem" do grupo | Testes da visão Dependente (Prompt 9) |
| **Um usuário podia se autoautorizar como consultor de terceiros** (o endpoint aceitava `cliente` arbitrário) | Revisão da fase de extras — corrigido forçando `cliente = usuário logado` |
| Sub-abas do painel do Gestor nunca renderizavam (condição de exibição contraditória no React) | Revisão manual da fase de extras |
| O painel do Gestor não tinha link na navegação — era inacessível pela interface | Sessão de validação simulada (`docs/validacao.md`) |

O padrão que se repetiu: o agente entrega rápido um esqueleto 90% correto, mas os 10% restantes
são justamente as regras de acesso — a parte mais sensível do projeto. A suíte de testes escrita
por critério de aceitação (um teste por regra do plano §5) foi o que transformou "parece que
funciona" em garantia.

## 4. Fricções técnicas dignas de nota

- **Custom User com login por e-mail**: o `UserManager` padrão do Django espera `username`;
  foi preciso um `UsuarioManager` próprio.
- **Serializers aninhados + test client do DRF**: o campo `divisoes` (lista de objetos) chega
  serializado de forma diferente no `APITestCase` e em requests reais; a solução foi ler
  `self.initial_data` diretamente.
- **`[]` é falsy em Python**: um teste media o dict de paginação em vez da lista vazia por causa
  de um `len(results or data)` — corrigido para `response.data.get("count", 0)`.
- **Estáticos em produção**: trocar `runserver` por gunicorn quebraria o CSS do Django Admin;
  resolvido com whitenoise + `collectstatic` no start do container.

## 5. Resultado final

- **5 visões** funcionais de ponta a ponta (Membro, Gestor, Dependente, Consultor, Admin), cada
  uma com painel próprio no React;
- **Todos os critérios do plano §5** cobertos por teste automatizado (rastreabilidade no DEVLOG);
- **Extras da fase de evolução entregues**: contas a pagar com lembretes por e-mail, metas de
  economia com aportes, importação de extrato CSV, recarga de mesada automática (por período) e
  manual (pelo gestor), filtros de transações por período/categoria/tipo;
- **142 testes, 0 falhas**, executáveis com um comando;
- `docker compose up --build` sobe banco, API (gunicorn) e frontend (nginx) do zero, e
  `seed_demo` popula um cenário completo (2 famílias, 1 república, 2 consultores com carteira,
  6 meses de histórico para os gráficos).

## 6. Avaliação do processo com agentes

**Ganhos**: velocidade brutal no scaffold e nas camadas repetitivas (serializers, viewsets,
telas CRUD); o agente também escreveu a suíte de testes que pegou os próprios bugs dele.

**Riscos observados**: sem revisão humana e sem testes, os furos de permissão teriam ido para a
entrega — e eram exatamente do tipo que não aparece em uso casual (exigem um segundo usuário
malicioso). A prática que funcionou: **pedir o teste junto com a feature e tratar o DEVLOG como
diário de bordo obrigatório**.

**Divisão de trabalho que emergiu**: humano define escopo, critérios e revisa diffs; agente
implementa, testa e documenta; os testes arbitram.
