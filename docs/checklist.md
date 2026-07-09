# Checklist — Versão 1 (MVP: Membro, Gestor, Administrador)

## Prompt 0 — Contexto, arquitetura e documentação inicial
- [x] Criar docs/plano.md
- [x] Criar DEEPSEEK.md
- [x] Criar docs/arquitetura.md
- [x] Criar docs/checklist.md

## Prompt 1 — Infraestrutura base
- [ ] docker-compose.yml (serviços `db` + `backend`)
- [ ] Projeto Django em `backend/` com Django REST Framework
- [ ] `.env` e `.env.example`
- [ ] Conexão PostgreSQL por variáveis de ambiente
- [ ] Endpoint `GET /api/health/` → 200
- [ ] `requirements.txt`
- [ ] Verificar: `docker compose up` → `http://localhost:8000/api/health/`

## Prompt 2 — Modelo de dados + migrações
- [ ] Custom User (`AbstractUser`) com login por e-mail e `papel_sistema`
- [ ] Models MVP: Conta, Categoria, Transacao, Grupo, MembroGrupo, Orcamento, DivisaoDespesa
- [ ] Models evolução (sem endpoints): Mesada, AutorizacaoConsultor, ContaAPagar, Recomendacao
- [ ] Validações de integridade nos models (FK, unicidade, soma das partes)
- [ ] Gerar e rodar migrações no container

## Prompt 3 — Autenticação por token + Django Admin
- [ ] Endpoint `POST /api/registro/`
- [ ] Endpoint `POST /api/login/` → retorna token
- [ ] Endpoint `GET /api/me/`
- [ ] TokenAuthentication configurado
- [ ] Django Admin com entidades registradas
- [ ] README: como criar superusuário

## Prompt 4 — API CRUD + permissões por visão
- [ ] Serializers para cada entidade MVP
- [ ] ViewSets REST para cada entidade
- [ ] Classes de permissão: `IsOwner`, `IsAdmin`, `IsGestorDoGrupo`, `IsMembroDoGrupo`
- [ ] Membro: CRUD próprio, vê grupo mas não administra
- [ ] Gestor: administra grupo, não vê finanças pessoais alheias
- [ ] Admin: gerencia usuários/categorias padrão, nunca acessa finanças
- [ ] Requisições sem token → 401

## Prompt 5 — Regras de negócio: grupo, divisão de despesas, "quem deve a quem"
- [ ] Criar grupo (criador vira responsável)
- [ ] Convidar/adicionar membros ao grupo
- [ ] Registrar despesa do grupo com divisão
- [ ] Invariante da soma: recusar se Σ partes ≠ valor total
- [ ] Divisão por valores definidos + opção de partes iguais
- [ ] Endpoint "quem deve a quem" no grupo
- [ ] Orçamento do grupo: previsto × realizado por categoria

## Prompt 6 — Testes automáticos
- [x] Testes de acesso e isolamento (Membro, Gestor, Admin)
- [x] Testes de integridade (soma das partes, FK inválidas)
- [x] Testes de CRUD básico por entidade
- [x] Comando único: `docker compose exec backend python manage.py test`
- [x] Atualizar DEVLOG.md com bugs encontrados pelos testes

## Prompt 7 — Frontend React
- [ ] Serviço `frontend` no docker-compose
- [ ] Cliente de API com gerenciamento de token
- [ ] Telas de cadastro e login
- [ ] Painel Membro: saldo, receitas/despesas por categoria, orçamento pessoal
- [ ] Painel Gestor: orçamento do grupo, gasto por categoria, "quem deve a quem"
- [ ] Visão Administrador: gestão de usuários e categorias padrão
- [ ] Gráficos Recharts (pizza + barra)
- [ ] Roteamento que mostra a visão correta conforme o usuário logado

## Prompt 8 — Empacotamento para entrega
- [ ] Dockerfile para backend
- [ ] Dockerfile para frontend (build + servir)
- [ ] docker-compose com `db` + `backend` + `frontend`
- [ ] Comando `seed_demo` (dados de demonstração)
- [ ] README.md completo (projeto, como subir, superusuário, testes, demo)
- [ ] `docker compose up` sobe tudo do zero

## Evolução (pós-MVP)

### Prompt 9 — Visão Dependente / mesada
- [ ] Mesada com valor, período de recarga e saldo atual
- [ ] Dependente vê apenas a própria mesada e lança os próprios gastos
- [ ] Gasto acima do limite bloqueado
- [ ] Testes e tela no frontend

### Prompt 10 — Visão Consultor
- [ ] AutorizacaoConsultor liga consultor a cliente (leitura/comentar)
- [ ] Consultor só enxerga clientes autorizados, modo leitura
- [ ] Recomendação: só criada por consultor com autorização válida
- [ ] Testes e tela de carteira de clientes
