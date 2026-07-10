# DEEPSEEK.md — NossoBolso (Finanças Compartilhadas)

Aplicação CRUD de finanças pessoais e de grupo, com cinco visões de usuário.

## Stack

- **Backend:** Python 3.11 com Django 4.2 + Django REST Framework 3.14
- **Banco:** PostgreSQL 15
- **Frontend:** React (Vite)
- **Autenticação:** TokenAuthentication do DRF
- **Infra:** Docker + docker-compose (serviços: `db`, `backend`, `frontend`)

## Estrutura do projeto

```
/
├── docker-compose.yml
├── .env / .env.example
├── README.md
├── CLAUDE.md
├── DEEPSEEK.md
├── DEVLOG.md
├── docs/
│   ├── plano.md
│   ├── arquitetura.md
│   └── checklist.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── manage.py
│   └── core/
│       ├── settings.py
│       ├── urls.py
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── permissions.py
│       ├── admin.py
│       └── tests/
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    └── src/
```

## Comandos do repositório

```bash
# Subir ambiente completo (build + run)
docker compose up --build

# Subir em segundo plano
docker compose up -d --build

# Parar os serviços
docker compose down

# Rodar migrações
docker compose exec backend python manage.py migrate

# Criar superusuário (Administrador)
docker compose exec backend python manage.py createsuperuser

# Rodar testes
docker compose exec backend python manage.py test

# Popular dados de demonstração (2 famílias, república, consultores, 6 meses de histórico)
docker compose exec backend python manage.py seed_demo

# Lembretes por e-mail (contas a pagar vencendo + orçamentos estourados)
docker compose exec backend python manage.py enviar_lembretes --dias 3

# Recarga de mesadas em lote (também acontece automaticamente ao consultar/gastar)
docker compose exec backend python manage.py recarregar_mesadas

# Ver logs do backend
docker compose logs -f backend

# Acessar shell do Django
docker compose exec backend python manage.py shell

# Resetar o banco (recriar do zero)
docker compose down -v
docker compose up --build
```

## Visões de usuário

| Visão | Papel no sistema | O que acessa |
|---|---|---|
| Membro | `comum` | Próprias transações, contas, categorias, orçamentos, contas a pagar, metas, importação CSV, autorização de consultores |
| Gestor | `comum` | Orçamento do grupo, lançamentos do grupo, "quem deve a quem", mesadas (criar/recarregar) |
| Dependente | `comum` | Apenas a própria mesada (recarga automática por período) e gastos pessoais |
| Consultor | `comum` | Clientes que o autorizaram, em modo leitura; recomendações se nível "comentar" |
| Administrador | `admin` | Gestão de usuários e categorias padrão (Django Admin + API); nunca acessa finanças |

## Papéis definidos por relacionamento

O `papel_sistema` do usuário é apenas `comum` ou `admin`. Os demais papéis (responsável, membro, dependente, consultor) são definidos por relacionamento:

- **No grupo:** `MembroGrupo.papel_no_grupo` → `responsavel` | `membro` | `dependente`
- **Consultor:** `AutorizacaoConsultor` liga consultor a cliente

Uma mesma pessoa pode ser responsável de um grupo, membro de outro e dependente em outro — sem alterar o cadastro.

## Convenções

- Custom User (`AbstractUser`) com login por e-mail (`email` como `USERNAME_FIELD`)
- Campo `papel_sistema`: `comum` ou `admin`
- Papéis de grupo definidos via `MembroGrupo.papel_no_grupo`
- Divisão de despesas: valores definidos por lançamento + opção de partes iguais
- Gráficos: somente o essencial (Recharts: pizza por categoria + barra previsto × realizado)
- Código em português (nomes de models, campos, variáveis)
- Banco cria tabelas no schema `public` do PostgreSQL via migrações do Django
