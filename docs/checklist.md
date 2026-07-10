# Checklist — Versão 1 (MVP: Membro, Gestor, Administrador)

## Prompt 0 — Contexto, arquitetura e documentação inicial
- [x] Criar docs/plano.md
- [x] Criar DEEPSEEK.md
- [x] Criar docs/arquitetura.md
- [x] Criar docs/checklist.md

## Prompt 1 — Infraestrutura base
- [x] docker-compose.yml (serviços `db` + `backend`)
- [x] Projeto Django em `backend/` com Django REST Framework
- [x] `.env` e `.env.example`
- [x] Conexão PostgreSQL por variáveis de ambiente
- [x] Endpoint `GET /api/health/` → 200
- [x] `requirements.txt`
- [x] Verificar: `docker compose up` → `http://localhost:8000/api/health/`

## Prompt 2 — Modelo de dados + migrações
- [x] Custom User (`AbstractUser`) com login por e-mail e `papel_sistema`
- [x] Models MVP: Conta, Categoria, Transacao, Grupo, MembroGrupo, Orcamento, DivisaoDespesa
- [x] Models evolução (sem endpoints): Mesada, AutorizacaoConsultor, ContaAPagar, Recomendacao
- [x] Validações de integridade nos models (FK, unicidade, soma das partes)
- [x] Gerar e rodar migrações no container

## Prompt 3 — Autenticação por token + Django Admin
- [x] Endpoint `POST /api/registro/`
- [x] Endpoint `POST /api/login/` → retorna token
- [x] Endpoint `GET /api/me/`
- [x] TokenAuthentication configurado
- [x] Django Admin com entidades registradas
- [x] README: como criar superusuário

## Prompt 4 — API CRUD + permissões por visão
- [x] Serializers para cada entidade MVP
- [x] ViewSets REST para cada entidade
- [x] Classes de permissão: `IsOwner`, `IsAdmin`, `IsGestorDoGrupo`, `IsMembroDoGrupo`
- [x] Membro: CRUD próprio, vê grupo mas não administra
- [x] Gestor: administra grupo, não vê finanças pessoais alheias
- [x] Admin: gerencia usuários/categorias padrão, nunca acessa finanças
- [x] Requisições sem token → 401

## Prompt 5 — Regras de negócio: grupo, divisão de despesas, "quem deve a quem"
- [x] Criar grupo (criador vira responsável)
- [x] Convidar/adicionar membros ao grupo
- [x] Registrar despesa do grupo com divisão
- [x] Invariante da soma: recusar se Σ partes ≠ valor total
- [x] Divisão por valores definidos + opção de partes iguais
- [x] Endpoint "quem deve a quem" no grupo
- [x] Orçamento do grupo: previsto × realizado por categoria

## Prompt 6 — Testes automáticos
- [x] Testes de acesso e isolamento (Membro, Gestor, Admin)
- [x] Testes de integridade (soma das partes, FK inválidas)
- [x] Testes de CRUD básico por entidade
- [x] Comando único: `docker compose exec backend python manage.py test`
- [x] Atualizar DEVLOG.md com bugs encontrados pelos testes

## Prompt 7 — Frontend React
- [x] Serviço `frontend` no docker-compose
- [x] Cliente de API com gerenciamento de token
- [x] Telas de cadastro e login
- [x] Painel Membro: saldo, receitas/despesas por categoria, orçamento pessoal
- [x] Painel Gestor: orçamento do grupo, gasto por categoria, "quem deve a quem"
- [x] Visão Administrador: gestão de usuários e categorias padrão
- [x] Gráficos Recharts (pizza + barra)
- [x] Roteamento que mostra a visão correta conforme o usuário logado

## Prompt 8 — Empacotamento para entrega
- [x] Dockerfile para backend (CMD com migrate + runserver)
- [x] Dockerfile para frontend (multi-stage: node build + nginx serve)
- [x] docker-compose com `db` + `backend` + `frontend`
- [x] Comando `seed_demo` (dados de demonstração)
- [x] README.md completo (projeto, como subir, superusuário, testes, demo)
- [x] `docker compose up` sobe tudo do zero

## Evolução (pós-MVP)

### Prompt 9 — Visão Dependente / mesada
- [x] Mesada com valor, período de recarga e saldo atual
- [x] Dependente vê apenas a própria mesada e lança os próprios gastos
- [x] Gasto acima do limite bloqueado
- [x] Testes e tela no frontend

### Prompt 10 — Visão Consultor
- [x] AutorizacaoConsultor liga consultor a cliente (leitura/comentar)
- [x] Consultor só enxerga clientes autorizados, modo leitura
- [x] Recomendação: só criada por consultor com autorização válida
- [x] Testes e tela de carteira de clientes

### Prompt 11 — Revisão final
- [x] Suíte de testes completa: 99 testes, 0 falhas
- [x] Dockerfile backend + frontend ok, docker compose up funcional
- [x] README, DEVLOG e checklist atualizados
- [x] Todas as regras de acesso do plano (§5) cobertas por teste

## Fase de fechamento (etapas 12–15)

### Rebranding
- [x] Nome NossoBolso no frontend, no repositório GitHub e (manual) na pasta local

### Extras do plano §1 (coluna "Evoluções")
- [x] Contas a pagar: API + aba no painel Membro + filtro por pago
- [x] Lembretes de vencimento e orçamento estourado por e-mail (`enviar_lembretes`)
- [x] Metas de economia: model + API + aba com barra de progresso e aportes
- [x] Importação de extrato CSV em lote (com relatório de erros por linha)

### Pendências do plano §7
- [x] Recarga de mesada automática por período (lazy + comando `recarregar_mesadas`)
- [x] Recarga de mesada manual pelo gestor (aba "Mesadas" no painel Gestor)
- [x] Validação simulada com roteiro de cliente (`docs/validacao.md`)

### Robustez e qualidade
- [x] gunicorn + whitenoise + collectstatic no container do backend
- [x] Filtros de transações (período, categoria, tipo, grupo)
- [x] Fix de segurança: autorização de consultor força `cliente = usuário logado`
- [x] Fix: sub-abas do PainelGestor não renderizavam; link "Grupos" ausente na navegação
- [x] Feedback de erros da API nas telas; responsividade básica (nav + tabelas)
- [x] Fluxo completo de consultor na interface (autorizar por e-mail, revogar, reativar)
- [x] seed_demo completo: 2 famílias + república + 2 consultores + 6 meses de histórico

### Documentação
- [x] Diagrama ER (Mermaid) em docs/arquitetura.md
- [x] docs/relatorio.md — rascunho do relatório do processo com agentes
- [x] README atualizado (endpoints novos, usuários demo, comandos de rotina)
- [x] Suíte final: 142 testes, 0 falhas
