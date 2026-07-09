# DEVLOG — Finanças Compartilhadas

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
