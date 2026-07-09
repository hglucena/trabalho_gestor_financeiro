# Finanças Compartilhadas

Aplicação CRUD de finanças pessoais e de grupo, com cinco visões de usuário (Membro, Gestor, Dependente, Consultor, Administrador).

## Stack

- **Backend:** Python 3.11 + Django 4.2 + Django REST Framework 3.17
- **Banco:** PostgreSQL 15
- **Frontend:** React (Vite) + Tailwind CSS + Recharts
- **Autenticação:** TokenAuthentication do DRF
- **Infra:** Docker + docker-compose

## Visões de usuário

| Visão | O que acessa |
|---|---|
| **Membro** | Contas, transações e orçamentos pessoais; vê grupos mas não administra |
| **Gestor** | Painel do grupo: membros, orçamento, despesas divididas, "quem deve a quem" |
| **Dependente** | Apenas a própria mesada e gastos pessoais; limite de gasto bloqueado |
| **Consultor** | Carteira de clientes autorizados (modo leitura); cria recomendações (nível comentar) |
| **Administrador** | Gestão de usuários e categorias padrão; NUNCA acessa finanças alheias |

## Como subir

```bash
# Subir o ambiente completo (db + backend + frontend)
docker compose up --build

# Em segundo plano
docker compose up -d --build

# Parar os serviços
docker compose down
```

- **Frontend:** http://localhost:5173
- **API do backend:** http://localhost:8000
- **Django Admin:** http://localhost:8000/admin/

## Dados de demonstração

Após subir o ambiente, popule o banco com dados de exemplo:

```bash
docker compose exec backend python manage.py seed_demo
```

### Usuários de demonstração

| Nome | Email | Senha | Papel |
|---|---|---|---|
| João Silva | joao@demo.com | senha123 | Comum (responsável do grupo) |
| Maria Oliveira | maria@demo.com | senha123 | Comum (membro do grupo) |
| Administrador | admin@demo.com | admin123 | Admin |

Os dados incluem: contas, categorias, transações pessoais, grupo "República Central" com despesas divididas entre João e Maria (aluguel de R$ 600 e compras de R$ 200) e orçamentos.

## Criar superusuário (Administrador)

```bash
docker compose exec backend python manage.py createsuperuser
```

Preencha email, nome e senha. O superusuário é criado com `papel_sistema = "admin"` e tem acesso ao painel administrativo em http://localhost:8000/admin/.

## Endpoints da API

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/health/` | Health check |
| `POST` | `/api/registro/` | Cadastro de usuário comum |
| `POST` | `/api/login/` | Login — retorna token + dados do usuário |
| `GET` | `/api/me/` | Perfil do usuário logado |
| `GET/POST` | `/api/contas/` | Contas do usuário |
| `GET/POST` | `/api/transacoes/` | Transações (próprias + grupos) |
| `GET/POST` | `/api/grupos/` | Grupos de que participa |
| `GET` | `/api/grupos/{id}/quem_deve_a_quem/` | Saldo líquido por membro |
| `GET` | `/api/grupos/{id}/orcamento_resumo/` | Previsto × realizado por categoria |
| `GET/POST` | `/api/mesadas/` | Mesadas (gestor/dependente) |
| `GET/POST` | `/api/autorizacoes/` | Autorizações de consultor |
| `GET/POST` | `/api/recomendacoes/` | Recomendações de consultor |
| `GET` | `/api/consultor/clientes/` | Clientes autorizados do consultor |
| `GET` | `/api/consultor/clientes/{id}/transacoes/` | Transações do cliente (leitura) |
| `GET` | `/api/consultor/clientes/{id}/contas/` | Contas do cliente (leitura) |

## Rodar migrações

```bash
docker compose exec backend python manage.py migrate
```

## Rodar testes

```bash
docker compose exec backend python manage.py test
```

**99 testes, 0 falhas.**

## Resetar o banco

```bash
docker compose down -v
docker compose up --build
```
