# Finanças Compartilhadas

Aplicação CRUD de finanças pessoais e de grupo, com múltiplas visões de usuário (Membro, Gestor, Administrador).

## Stack

- **Backend:** Python 3.11 + Django 4.2 + Django REST Framework 3.17
- **Banco:** PostgreSQL 15
- **Frontend:** React (Vite) — em desenvolvimento
- **Autenticação:** TokenAuthentication do DRF
- **Infra:** Docker + docker-compose

## Como subir

```bash
# Subir o ambiente completo
docker compose up --build

# Em segundo plano
docker compose up -d --build

# Parar os serviços
docker compose down
```

A aplicação fica em http://localhost:8000.

## Criar superusuário (Administrador)

```bash
docker compose exec backend python manage.py createsuperuser
```

Preencha email, nome e senha. O superusuário é criado com `papel_sistema = "admin"` e tem acesso ao painel administrativo em http://localhost:8000/admin/.

## Endpoints da API

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/health/` | Health check (banco conectado?) |
| `POST` | `/api/registro/` | Cadastro de usuário comum |
| `POST` | `/api/login/` | Login — retorna token + dados do usuário |
| `GET` | `/api/me/` | Perfil do usuário logado |

## Rodar migrações

```bash
docker compose exec backend python manage.py migrate
```

## Rodar testes

```bash
docker compose exec backend python manage.py test
```

## Popular dados de demonstração

```bash
docker compose exec backend python manage.py seed_demo
```

## Resetar o banco

```bash
docker compose down -v
docker compose up --build
```
