# Finanças Compartilhadas

Aplicação CRUD de finanças pessoais e de grupo, com múltiplas visões de usuário.

## Stack

- **Backend:** Python com Django + Django REST Framework
- **Banco:** PostgreSQL 15
- **Frontend:** React (Vite)
- **Autenticação:** TokenAuthentication do DRF
- **Infra:** Docker + docker-compose (serviços: `db`, `backend`, `frontend`)

## Visões de usuário (MVP)

| Visão         | Papel no sistema | O que acessa                                                  |
|---------------|-----------------:|---------------------------------------------------------------|
| Membro        | `comum`          | Próprias transações, contas, categorias pessoais, orçamento pessoal |
| Gestor        | `comum`          | Orçamento do grupo, lançamentos do grupo, "quem deve a quem"  |
| Administrador | `admin`          | Gestão de usuários e categorias padrão (Django Admin + API)   |

## Papéis definidos por relacionamento

O `papel_sistema` do usuário é apenas `comum` ou `admin`. Os demais papéis (responsável, membro, dependente, consultor) são definidos por relacionamento:

- **No grupo:** `MembroGrupo.papel_no_grupo` → `responsavel` | `membro` | `dependente`
- **Consultor:** `AutorizacaoConsultor` liga consultor a cliente

Uma mesma pessoa pode ser responsável de um grupo, membro de outro e dependente em outro — sem alterar o cadastro.

## Comandos do repositório

```bash
# Subir ambiente completo
docker compose up --build

# Rodar migrações
docker compose exec backend python manage.py migrate

# Criar superusuário (Administrador)
docker compose exec backend python manage.py createsuperuser

# Rodar testes
docker compose exec backend python manage.py test

# Popular dados de demonstração
docker compose exec backend python manage.py seed_demo
```

## Convenções

- Custom User (`AbstractUser`) com login por e-mail (`email` como `USERNAME_FIELD`)
- Campo `papel_sistema`: `comum` ou `admin`
- Papéis de grupo definidos via `MembroGrupo.papel_no_grupo`
- Divisão de despesas: valores definidos por lançamento + opção de partes iguais
- Gráficos: somente o essencial (Recharts)
