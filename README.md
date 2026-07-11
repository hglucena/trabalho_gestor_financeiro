# NossoBolso

Aplicação CRUD de finanças pessoais e de grupo, com cinco visões de usuário (Membro, Gestor, Dependente, Consultor, Administrador).

## Stack

- **Backend:** Python 3.11 + Django 4.2 + Django REST Framework 3.17, servido por gunicorn + whitenoise
- **Banco:** PostgreSQL 15
- **Frontend:** React (Vite) + Tailwind CSS + Recharts, servido por nginx
- **Autenticação:** TokenAuthentication do DRF
- **Infra:** Docker + docker-compose

## Visões de usuário

| Visão | O que acessa |
|---|---|
| **Membro** | Contas (com saldo vivo), transações, categorias, orçamentos, contas a pagar, metas de economia; importa extrato CSV; autoriza/revoga consultores; vê grupos mas não administra |
| **Gestor** | Painel do grupo: membros, orçamento, despesas divididas, "quem deve a quem", mesadas (criar e recarregar) |
| **Dependente** | Apenas a própria mesada e gastos pessoais; gasto acima do saldo é bloqueado; recarga automática por período; metas próprias (ex.: juntar para um PS5) com aportes saindo da mesada |
| **Consultor** | Carteira de clientes autorizados (modo leitura); cria recomendações (nível comentar) |
| **Administrador** | Gestão de usuários e categorias padrão; NUNCA acessa finanças alheias |

## Tutorial: rodando o projeto do zero (passo a passo)

### 0. Pré-requisitos

- **Docker Desktop** instalado e **aberto** (ícone da baleia estável na bandeja) — [download](https://www.docker.com/products/docker-desktop/)
- **Git** instalado

### 1. Clonar o repositório

```bash
git clone https://github.com/hglucena/NossoBolso.git
cd NossoBolso
```

### 2. Subir o ambiente (banco + API + frontend)

```bash
docker compose up -d --build
```

A primeira execução baixa as imagens e compila tudo (2–5 minutos). As seguintes são rápidas.
O backend roda as migrações do banco automaticamente ao iniciar.

Confira se os três serviços subiram:

```bash
docker compose ps
```

Deve aparecer `db` (healthy), `backend` e `frontend` como `Up`.

### 3. Popular com os dados de demonstração

```bash
docker compose exec backend python manage.py seed_demo
```

Isso cria um cenário completo: **2 famílias** (Silva e Costa), **1 república** com 3 moradores,
**2 consultores** com carteiras de clientes, **6 meses de histórico** de transações (para os
gráficos), mesadas com gastos, contas a pagar, metas de economia e recomendações.

### 4. Acessar

| O quê | Endereço |
|---|---|
| **Aplicação** | http://localhost:5173 |
| API | http://localhost:8000/api/health/ |
| Django Admin | http://localhost:8000/admin/ |

### 5. Explorar cada visão (senha de todos: `senha123`)

| Faça login como... | Para ver... |
|---|---|
| `joao@demo.com` | **Membro + Gestor**: painel completo com saldo, gráfico donut, contas a pagar, metas, consultores; no menu "Grupos", administre a Família Silva (despesas divididas, quem deve a quem, mesada do Pedro) |
| `pedro@demo.com` | **Dependente**: só a mesada — registre um gasto, tente estourar o saldo (bloqueia!), crie uma meta "PS5" e guarde mesada nela |
| `carlos@demo.com` | **Consultor**: carteira com 3 clientes em modo leitura; deixe uma recomendação para o João |
| `maria@demo.com` | **Gestora da república**: 3 moradores dividindo aluguel, compras e internet |
| `admin@demo.com` (senha `admin123`) | **Admin**: usuários e categorias padrão — repare que ele não vê finanças de ninguém |

### 6. Parar / resetar

```bash
# Parar os serviços (mantém os dados)
docker compose down

# Resetar TUDO (apaga o banco) e recomeçar
docker compose down -v
docker compose up -d --build
docker compose exec backend python manage.py seed_demo
```

### Problemas comuns

- **"Impossível fazer login"** → o seed ainda não rodou; execute o passo 3.
- **Porta 5173 ou 8000 ocupada** → pare o que estiver usando a porta ou edite as portas no `docker-compose.yml`.
- **Docker não conecta** → o Docker Desktop precisa estar aberto antes do `docker compose up`.
- **Mudou código do frontend e não apareceu** → `docker compose up -d --build frontend` e recarregue com Ctrl+Shift+R.

## Dados de demonstração

Após subir o ambiente, popule o banco com um cenário completo (2 famílias, 1 república,
2 consultores com carteira de clientes e 6 meses de histórico de transações):

```bash
docker compose exec backend python manage.py seed_demo
```

### Usuários de demonstração (senha de todos: `senha123`)

| Grupo | Email | Papel |
|---|---|---|
| Família Silva | joao@demo.com | Gestor do grupo; cliente do Carlos (comentar) |
| Família Silva | ana@demo.com | Membro |
| Família Silva | pedro@demo.com | Dependente — mesada mensal de R$ 200 |
| República Central | maria@demo.com | Gestora; cliente do Carlos (leitura) |
| República Central | lucas@demo.com | Membro; cliente da Paula (leitura) |
| República Central | julia@demo.com | Membro |
| Família Costa | roberto@demo.com | Gestor; cliente do Carlos (comentar) |
| Família Costa | fernanda@demo.com | Membro; cliente da Paula (comentar) |
| Família Costa | bia@demo.com | Dependente — mesada semanal de R$ 80 |
| — | carlos@demo.com | Consultor com 3 clientes |
| — | paula@demo.com | Consultora com 2 clientes |
| — | admin@demo.com | Administrador (senha: `admin123`) |

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
| `GET/POST` | `/api/contas/` | Contas do usuário — retorna `saldo_atual` (saldo inicial + receitas − despesas; **pode ficar negativo**) |
| `GET/POST` | `/api/transacoes/` | Transações (filtros: `?data_inicio=&data_fim=&categoria=&tipo=&grupo=`) |
| `POST` | `/api/transacoes/importar_csv/` | Importa extrato CSV (`arquivo` + `conta`) |
| `GET/POST` | `/api/grupos/` | Grupos de que participa |
| `GET` | `/api/grupos/{id}/quem_deve_a_quem/` | Saldo líquido por membro |
| `GET` | `/api/grupos/{id}/orcamento_resumo/` | Previsto × realizado por categoria |
| `GET/POST` | `/api/mesadas/` | Mesadas (gestor/dependente) — recarga automática por período |
| `POST` | `/api/mesadas/{id}/recarregar/` | Recarga manual pelo gestor (`valor` opcional) |
| `GET/POST` | `/api/contas-a-pagar/` | Contas a pagar (filtro `?pago=true\|false`) |
| `POST` | `/api/contas-a-pagar/{id}/pagar/` | Marca como paga e lança a despesa na conta (`conta` opcional) — o saldo cai |
| `GET/POST` | `/api/metas/` | Metas de economia (dependentes também podem criar) |
| `POST` | `/api/metas/{id}/aportar/` | Aporte na meta — lança despesa na conta; para dependente, deduz da mesada (e respeita o saldo dela) |
| `GET/POST` | `/api/autorizacoes/` | Autorizações de consultor (aceita `consultor_email`) |
| `GET/POST` | `/api/recomendacoes/` | Recomendações de consultor |
| `GET` | `/api/consultor/clientes/` | Clientes autorizados do consultor |
| `GET` | `/api/consultor/clientes/{id}/transacoes/` | Transações do cliente (leitura) |
| `GET` | `/api/consultor/clientes/{id}/contas/` | Contas do cliente (leitura) |

### Formato do CSV de importação

```csv
data,descricao,valor,tipo,categoria
2026-07-01,Mercado,150.50,despesa,Alimentacao
02/07/2026,Salario,"3000,00",receita,Salario
```

Datas em `AAAA-MM-DD` ou `DD/MM/AAAA`; categoria inexistente é criada automaticamente para o usuário; linhas inválidas são reportadas sem abortar a importação.

## Comandos de rotina

```bash
# Lembretes por e-mail: contas a pagar vencendo e orçamentos estourados
# (por padrão imprime no console; configure EMAIL_BACKEND para envio real)
docker compose exec backend python manage.py enviar_lembretes --dias 3

# Recarga de mesadas em lote (a recarga também é automática ao consultar/gastar)
docker compose exec backend python manage.py recarregar_mesadas
```

## Rodar migrações

```bash
docker compose exec backend python manage.py migrate
```

## Rodar testes

```bash
docker compose exec backend python manage.py test
```

**165 testes, 0 falhas.**

## Regras de saldo

- O saldo de cada conta é **vivo**: `saldo_inicial + receitas − despesas`. Novas transações,
  pagamentos de contas a pagar e aportes em metas movimentam o saldo na hora.
- **O saldo pode ficar negativo** — decisão de projeto: a aplicação registra a realidade
  financeira e nunca bloqueia uma operação por saldo insuficiente. A única exceção é a mesada
  do dependente, que bloqueia gasto (ou aporte) acima do saldo disponível.

## Resetar o banco

```bash
docker compose down -v
docker compose up --build
```
