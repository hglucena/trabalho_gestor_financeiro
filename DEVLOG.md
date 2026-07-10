# DEVLOG — NossoBolso (Finanças Compartilhadas)

Diário de bordo do desenvolvimento com agente de código (Claude Code). A cada etapa registramos
o que o agente acertou de primeira, os bugs encontrados (e como foram pegos) e as decisões tomadas.
Etapas 0–11 correspondem à sequência de prompts planejada; as etapas 12+ são a fase de
fechamento (rebranding, extras da evolução e revisão final).

## Prompt 0–1: Infraestrutura base

**O que o agente acertou de primeira:**
- Docker Compose com healthcheck do PostgreSQL e dependência correta (`depends_on: service_healthy`)
- Django + DRF + PostgreSQL conectado via `dj-database-url`
- Endpoint `/api/health/` funcional
- `.env` e `.env.example` padronizados

**Ajustes necessários:**
- Fallback SQLite para desenvolvimento local sem Docker
- `ALLOWED_HOSTS` mais restritivo (`localhost,127.0.0.1`)

## Prompt 2: Modelo de dados

**Acertos:**
- Custom User (`AbstractUser`) com `USERNAME_FIELD = "email"` e `username = None`
- `UsuarioManager` customizado para `create_user(email, nome, password)`
- 12 modelos (8 MVP + 4 evolução)
- Constraints de unicidade: `MembroGrupo`, `DivisaoDespesa`, `Categoria`, `AutorizacaoConsultor`
- `clean()` com validações de integridade nos modelos `Transacao`, `Orcamento`, `DivisaoDespesa`

**Ajustes:**
- `UsuarioManager` precisou ser criado porque `UserManager.create_user()` padrão ainda espera `username`

## Prompt 3: Autenticação

**Acertos:**
- Registro com `papel_sistema="comum"` implícito (não exposto na API)
- Login retorna token + dados do usuário com `papel_sistema`
- Django Admin com todas as entidades registradas

**Sem ajustes necessários.**

## Prompt 4: API CRUD + Permissões (revisado)

**Acertos:**
- 11 classes de permissão reutilizáveis e testáveis
- 6 viewsets + endpoints aninhados
- `NaoAdmin` bloqueia admin de conteúdo financeiro (403)

**Bugs encontrados e corrigidos:**
1. **GrupoViewSet sem proteção de escrita** — qualquer membro podia editar/deletar o grupo. Corrigido com `IsOwnerOrReadOnly` para `update`/`destroy`.
2. **CategoriaViewSet sem `IsOwner`** — usuário A podia editar categoria de B se soubesse o ID. Corrigido com `get_permissions()` condicional.
3. **Admin bloqueado da API de categorias** — `NaoAdmin` impedia admin de criar categorias padrão. Corrigido com queryset/admin separados.
4. **OrcamentoViewSet sem validação de gestor** — qualquer um criava orçamento de grupo. Corrigido com verificação em `perform_create`.
5. **MembroGrupoSerializer exigia `grupo` no body** — adicionado `"grupo"` ao `read_only_fields`.

## Prompt 5: Regras de negócio

**Acertos:**
- Divisão em partes iguais com ajuste de centavos no primeiro participante
- Invariante da soma validada no serializer
- `quem_deve_a_quem` com saldo líquido por membro
- `orcamento_resumo` com previsto × realizado por categoria

**Bugs encontrados e corrigidos:**
1. **Divisão explícita 400** — `DivisaoDespesaSerializer.transacao` era obrigatório no body. Adicionado ao `read_only_fields`.
2. **Nested serializer + DRF test client** — `JSONField` e `DivisaoDespesaSerializer` aninhado causam `TypeError` nos testes DRF (dados chegam como string no `self.initial_data`). Solução: usar `self.initial_data` diretamente para leitura de `divisoes` (campo não declarado no Meta.fields).

## Prompt 6: Testes automáticos

**Resultado final: 67 testes, 0 falhas, 0 erros.**

```
test_auth.py          —  8 testes (registro, login, /me/, superuser)
test_permissions.py   — 20 testes (isolamento Membro/Gestor/Admin)
test_crud.py          — 25 testes (CRUD por entidade)
test_integrity.py     — 10 testes (invariante soma, FK, validações modelo)
test_business.py      —  4 testes (regras de negócio)
```

**Cobertura dos critérios do plano (§5 e §6):**

| Critério | Teste |
|---|---|
| Usuário só acessa próprias transações | `test_outro_nao_ve_contas_do_gestor`, `test_membro_nao_edita_conta_gestor` |
| Admin nunca acessa finanças | `test_admin_nao_ve_transacoes`, `test_admin_nao_ve_contas`, `test_admin_nao_cria_conta` |
| Responsável vê grupo, não finanças pessoais | `test_membro_nao_ve_transacao_pessoal_gestor`, `test_membro_ve_transacao_do_grupo` |
| Sem token → negado | `test_sem_token_negado` |
| Só responsável administra o grupo | `test_membro_nao_edita_grupo`, `test_membro_nao_deleta_grupo`, `test_membro_nao_adiciona_membro` |
| Despesa dividida: soma = total | `test_divisao_soma_diferente_valor_recusada` (serializer), `test_divisao_soma_exata_aceita` |
| Transação → conta/categoria válidas | `test_transacao_conta_de_outro_usuario`, `test_transacao_categoria_pessoal_de_outro_usuario` |

**Observações sobre o processo de teste:**
- Os testes de permissão capturaram os bugs 1-4 do Prompt 4 (listados acima) — todos já corrigidos
- O `IsOwner` (`obj.usuario_id == request.user.id`) efetivamente impede acesso cross-user
- `NaoAdmin` (`papel_sistema != "admin"`) é a barreira mais simples e eficaz
- Testes com nested data (`divisoes`) no DRF test client são frágeis devido a diferenças de serialização entre `APITestCase` e requests reais. A funcionalidade foi validada manualmente (Prompt 5: 20/20)
- A divisão entre `setUp` e testes por classe exige cuidado com IDs de usuário que variam conforme ordem de execução

## Prompt 7: Frontend React

**Acertos:**
- Vite + Tailwind + Recharts configurados rapidamente
- Proxy da API via Vite no dev, nginx no build de produção
- 3 painéis (Membro, Gestor, Admin) com CRUD funcional
- Gráfico de pizza (Membro) e barra previsto × realizado (Gestor)

**Ajustes:**
- Nenhum necessário — o frontend subiu de primeira

## Prompt 8: Empacotamento para entrega

**Acertos:**
- Backend Dockerfile com `CMD` (migrate + runserver)
- Frontend multi-stage (node build + nginx serve com proxy reverso)
- `docker compose up --build` sobe db + backend + frontend
- Comando `seed_demo` com 3 usuários, grupo, despesas divididas, orçamentos

**Sem ajustes necessários.**

## Prompt 9: Visão Dependente (evolução)

**Acertos:**
- `MesadaViewSet` com queryset condicional (dependente vê só a sua; gestor vê do grupo)
- Validação de limite no `TransacaoViewSet.perform_create()` — bloqueia gasto acima do `saldo_atual`
- Dedução automática do saldo da mesada a cada despesa
- `PainelDependente.jsx` com cartão de mesada e formulário de gasto
- Querysets ajustados: dependente não vê grupos, transações do grupo, orçamentos do grupo

**Bugs encontrados e corrigidos:**
1. **Dependente ainda via membros do grupo** — `IsGestorDoGrupoByKwarg` permitia leitura para qualquer membro. Corrigido com `.exclude(papel_no_grupo="dependente")`.
2. **Dependente acessava `quem_deve_a_quem`** — `GrupoViewSet.get_queryset()` agora exclui grupos onde o usuário é dependente (retorna 404).

## Prompt 10: Visão Consultor (evolução)

**Acertos:**
- `AutorizacaoConsultorViewSet` — cliente autoriza/revoga consultor com nível (leitura/comentar)
- `RecomendacaoViewSet` — consultor com nível "comentar" cria recomendações
- `ConsultorClientesView` — lista apenas clientes com autorização ativa
- `ConsultorClienteTransacoesView` / `ConsultorClienteContasView` — leitura com `IsConsultorAutorizado`
- `PainelConsultor.jsx` — carteira de clientes, finanças em modo leitura, criação de recomendações
- Distinção entre nível "leitura" (não pode criar recomendação) e "comentar" (pode)

**Bugs encontrados e corrigidos:**
1. **Teste `test_consultor_nao_pode_criar_transacao_para_cliente`** — removido (a validação do model já impede criar transação com conta de outro usuário). Substituído por teste que verifica que consultor não edita transação do cliente via PATCH (404).
2. **Teste de lista vazia usava `len(results or data)`** — `[]` é falsy em Python, caía no `or` e media o dict de paginação (4 chaves). Corrigido para `response.data.get("count", 0)`.

## Prompt 11: Revisão final

**Resultado final: 99 testes, 0 falhas, 0 erros.**

```
test_auth.py          —  8 testes (registro, login, /me/, superuser)
test_permissions.py   — 20 testes (isolamento Membro/Gestor/Admin)
test_crud.py          — 25 testes (CRUD por entidade)
test_integrity.py     — 10 testes (invariante soma, FK, validações modelo)
test_business.py      —  4 testes (regras de negócio)
test_dependente.py    — 17 testes (acesso isolado, limite mesada, dedução saldo)
test_consultor.py     — 15 testes (autorização, leitura vs comentar, isolamento)
```

**Cobertura dos critérios do plano (§5 e §6):**

| Critério | Cobertura |
|---|---|
| §5.1 Dependente não acessa nada além da mesada | `test_dependente_nao_ve_grupos`, `test_dependente_nao_ve_transacoes_do_grupo`, `test_dependente_nao_ve_orcamentos_do_grupo` |
| §5.2 Consultor só enxerga clientes autorizados (leitura) | `test_consultor_autorizado_ve_clientes`, `test_consultor_nao_autorizado_nao_ve_cliente`, `test_consultor_nao_edita_transacao_do_cliente` |
| §5.3 Responsável vê grupo, não finanças pessoais | `test_membro_nao_ve_transacao_pessoal_gestor` |
| §5.4 Admin nunca acessa finanças | `test_admin_nao_ve_transacoes`, `test_admin_nao_ve_contas` |
| §5.5 Cada usuário só acessa as próprias transações | `test_outro_nao_ve_contas_do_gestor` |
| §5.6 Recomendação só por consultor autorizado | `test_consultor_leitura_nao_cria_recomendacao`, `test_consultor_comentar_cria_recomendacao` |
| §5.7 Soma das partes = valor total | `test_divisao_soma_diferente_valor_recusada` |
| §5.8 Transação com conta/categoria válidas | `test_transacao_conta_de_outro_usuario` |
| §5.9 Saldo da mesada respeita o limite | `test_gasto_acima_do_limite_bloqueado`, `test_gasto_apos_esgotar_saldo_bloqueado`, `test_gastos_acumulados_deduzem_saldo` |

**Infraestrutura:**
- `docker compose up --build` sobe os 3 serviços (db, backend, frontend)
- Backend executa `migrate` automaticamente no CMD do Dockerfile
- Frontend com build multi-stage (Vite → nginx) + proxy reverso para `/api/`
- `seed_demo` popula banco com dados de demonstração

**Regras de acesso do plano — cobertura completa. Nenhum critério do §5 ficou sem teste.**

## Etapa 12: Rebranding — NossoBolso

**Prompt (resumo):** "Gostei do NossoBolso. Bote esse nome em todas referências ao nome do
projeto no front, na pasta do repositório e no nome do repositório no github."

- 6 referências trocadas no frontend (`index.html`, `package.json`, `package-lock.json`,
  `Layout.jsx`, `LoginPage.jsx`)
- Repositório GitHub renomeado: `trabalho_gestor_financeiro` → `hglucena/NossoBolso`
  (remote atualizado automaticamente pelo `gh repo rename`)
- Renomeação da pasta local ficou manual (Windows bloqueia renomear pasta em uso pelo VSCode)

## Etapa 13: Extras da evolução — contas a pagar, metas, CSV, lembretes, filtros

**Prompt (resumo):** "Faça isso daqui tudo" — a lista completa de pendências levantada na
revisão: extras do plano §1, pendências do §7, robustez de produção, qualidade de vida no
frontend e material do relatório.

**Backend:**
- `ContaAPagar` ganhou serializer + viewset (`/api/contas-a-pagar/`, filtro `?pago=`) — o model
  já existia desde o Prompt 2
- Novo model `MetaEconomia` (migração 0002) com `POST /api/metas/{id}/aportar/` e percentual
  calculado no serializer
- `POST /api/transacoes/importar_csv/` — importação de extrato em lote; linhas inválidas viram
  relatório de erros sem abortar; categoria inexistente é criada para o usuário; dependentes são
  bloqueados (bypassariam a regra da mesada)
- `manage.py enviar_lembretes` — e-mails de contas a pagar vencendo e orçamentos estourados
  (EMAIL_BACKEND console por padrão)
- Filtros em `/api/transacoes/`: `data_inicio`, `data_fim`, `categoria`, `tipo`, `grupo`
- Produção: gunicorn (3 workers) + whitenoise + `collectstatic` no CMD do Dockerfile

**Bug de segurança encontrado e corrigido:**
1. **Autoautorização de consultor** — `AutorizacaoConsultorViewSet.perform_create()` salvava o
   payload cru: qualquer usuário podia POSTar `{consultor: eu, cliente: vítima}` e ganhar acesso
   de leitura às finanças de terceiros. Corrigido: `cliente` é sempre o usuário logado
   (read-only no serializer), com validações de duplicidade e de autoconsultoria. O endpoint
   também passou a aceitar `consultor_email` (a tela usa e-mail em vez de ID).

**Bugs de frontend encontrados e corrigidos:**
2. **Sub-abas do PainelGestor nunca renderizavam** — o bloco de detalhe exigia `aba === "detalhe"`,
   mas clicar numa sub-aba mudava `aba` para "membros"/"transacoes"/..., escondendo tudo.
3. **Painel do Gestor inacessível** — não havia link "Grupos" na navegação; só chegava lá quem
   digitasse a URL.

**Frontend:**
- Painel Membro: abas novas "A Pagar", "Metas" (barra de progresso + aporte) e "Consultores"
  (autorizar por e-mail, revogar/reativar, ver recomendações recebidas); botão "Importar CSV"
- Painel Gestor: aba "Mesadas" (criar e recarregar); mensagens de erro da API nas telas
- Responsividade: navegação com quebra de linha e tabelas com rolagem horizontal

## Etapa 14: Recarga automática de mesada

**Prompt (resumo):** "Você não pode fazer recarga automática da mesada não? É bem simples."

- Campo `Mesada.ultima_recarga` (migração 0003) + método `recarregar_se_devido()`: credita o
  valor da mesada a cada período vencido (semanal=7d, quinzenal=15d, mensal=30d)
- Recarga **preguiçosa**: aplicada ao consultar `/api/mesadas/` e antes da validação de limite ao
  lançar um gasto — funciona sem cron
- `manage.py recarregar_mesadas` para agendamento em lote
- Recarga manual pelo gestor mantida (`POST /api/mesadas/{id}/recarregar/`)
- Tela do dependente mostra a data da próxima recarga

## Etapa 15: seed_demo completo + documentação final

- `seed_demo` reescrito: 11 usuários (Família Silva, República Central com 3 moradores,
  Família Costa, 2 consultores com carteiras de 3 e 2 clientes), **6 meses de histórico**
  (~180 transações pessoais + 4 meses de despesas divididas por grupo) para os gráficos,
  mesadas com gastos, contas a pagar (incluindo vencida e paga), metas (incluindo uma concluída)
  e recomendações. Idempotente: histórico não é duplicado ao rodar duas vezes.
- Diagrama ER (Mermaid) em `docs/arquitetura.md`; decisões do §7 do plano atualizadas
- `docs/validacao.md` — sessão de validação simulada com o roteiro do cliente (plano §6),
  incluindo os ajustes que ela gerou
- `docs/relatorio.md` — rascunho do relatório sobre o processo com agentes

**Resultado final: 142 testes, 0 falhas** (99 anteriores + 43 novos em `test_extras.py`:
contas a pagar, recarga manual e automática, metas, CSV, filtros, segurança de autorização e
lembretes por e-mail).

## Etapa 16: Bug pego em uso real com os dados de demonstração

Ao rodar a aplicação com o seed completo, o gestor João caiu no **painel de dependente**, vendo
a mesada do Pedro como se fosse dele — e com "duas abas iguais" no menu.

**Causa:** o frontend classificava como dependente qualquer usuário cuja consulta a
`/api/mesadas/` retornasse resultados. Mas o **gestor também enxerga mesadas** (as dos
dependentes do grupo). O seed antigo não tinha nenhuma mesada, então a heurística nunca falhava
— foi o cenário de dados rico que expôs o bug.

**Correção:** dependente é quem tem mesada **própria** (`m.dependente === user.id`), aplicado no
roteador (`App.jsx`), no menu (`Layout.jsx`) e no cartão da mesada (`PainelDependente.jsx`).

**Lição para o relatório:** dados de demonstração realistas funcionam como teste de integração
manual — heurísticas de interface que passam com dados pobres quebram com dados plausíveis.

## Etapa 17: Saldo vivo, pagamento com lançamento e metas do dependente

**Prompts (resumo):** "quando marcar alguma conta como paga o saldo deve diminuir; quando
adicionarmos um valor economizado na meta o saldo deve diminuir; mesma coisa na nova
transação/receita"; "o saldo também pode ficar negativo, lembre disso"; "bote também aba de
metas para o dependente com mesada, tipo o filho quer comprar um PS5".

**Decisão de domínio — saldo vivo:** o saldo deixou de ser estático (`saldo_inicial`) e passou a
ser calculado: `saldo_inicial + receitas − despesas` (campo `saldo_atual` no serializer de
Conta). Tudo que movimenta dinheiro gera uma **transação**, e o saldo deriva delas:

- `POST /api/contas-a-pagar/{id}/pagar/` marca como paga e lança a despesa
  "Pagamento: <descrição>" na conta do usuário (categoria padrão "Contas"); pagar duas vezes → 400
- `POST /api/metas/{id}/aportar/` lança a despesa "Aporte na meta: <nome>" (categoria "Poupanca")
- Transações comuns (receita/despesa) já refletem no saldo automaticamente

**Decisão de projeto (registrada):** o saldo **pode ficar negativo** — nenhuma operação é
bloqueada por saldo insuficiente. Exceção única: a mesada do dependente (regra §5.9 do plano).

**Metas do dependente:** dependentes criam metas próprias (ex.: PS5) e guardam dinheiro **da
mesada** — o aporte respeita o saldo da mesada (403 acima do limite), deduz dela e vira
transação. Seção "Minhas Metas" no painel do dependente com barra de progresso; seed ganhou as
metas "PS5" (Pedro) e "Bicicleta" (Bia).

**Gráfico:** categoria padrão "Cartão de Crédito" adicionada, com faturas mensais no histórico
do seed (João, Maria e Roberto) para aparecer na pizza de despesas; categorias "Contas" e
"Poupanca" também viraram padrão (usadas pelos lançamentos automáticos).

**UI:** saldo negativo aparece em vermelho (total e por conta); painéis recarregam contas e
transações após pagar/aportar/lançar.

**Resultado: 150 testes, 0 falhas** (8 novos: 5 de saldo vivo/pagamento e 3 de metas do
dependente com mesada).
