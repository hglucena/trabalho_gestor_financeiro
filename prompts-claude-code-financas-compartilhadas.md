# Sequência de prompts para o Claude Code — Finanças Compartilhadas (CRUD v1)

Cole **um prompt de cada vez**. Depois de cada passo: revise o que o agente fez, rode/teste, faça o commit, e só então passe para o próximo. A sequência constrói primeiro o **MVP com as três visões (Membro, Gestor, Administrador)**, que é a Versão 1 do plano; as visões Dependente e Consultor entram como evolução opcional (prompts 9 e 10).

---

## Antes de começar

1. Crie uma pasta vazia para o projeto e abra o Claude Code nela (`claude` no terminal, ou a aba Code no app).
2. Salve o plano da Atividade 03 dentro da pasta como `docs/plano.md` (exporte o `.docx` para texto/markdown e cole). Assim o agente lê a fonte da verdade direto do repositório. Se não der para converter fácil, cole o texto do plano na primeira mensagem.
3. Inicialize o git na pasta (`git init`).

**Workflow recomendado (rende muito):**
- Use **plan mode** (`/plan` ou Shift+Tab) nos passos maiores (0, 1, 4, 6, 7): o agente propõe um plano antes de mexer no código, você aprova, evita retrabalho.
- Depois de cada passo, veja o diff (`/diff`), **rode o que foi feito** e só então siga. Não aceite código no piloto automático — a nota e o aprendizado são de vocês.
- Peça commit ao fim de cada passo (os prompts já pedem).
- Mantenham um `DEVLOG.md`: a cada passo, anotem o que o agente acertou de primeira, onde errou/precisou de ajuste e as decisões tomadas. Isso vira o recheio do relatório sobre "o processo de desenvolvimento com agentes".
- Modelo: vale usar Opus nos passos de arquitetura e permissões (0, 4, 6) e deixar o Sonnet nos demais. Troca com `/model`.

---

## Os prompts

### Prompt 0 — Contexto, arquitetura e checklist  *(use plan mode)*
```
Leia o arquivo @docs/plano.md por completo — é a proposta da nossa aplicação "Finanças Compartilhadas", uma app CRUD com múltiplas visões de usuário.

Antes de escrever qualquer código:
1. Crie um CLAUDE.md descrevendo o projeto, a stack (Django + Django REST Framework + PostgreSQL no backend, React no frontend, autenticação por token do DRF, tudo em containers Docker) e os comandos do repositório (subir ambiente, rodar migrações, rodar testes).
2. Crie docs/arquitetura.md com a estrutura de pastas (backend e frontend separados), as entidades do modelo de dados e as regras de acesso por visão.
3. Crie docs/checklist.md com as tarefas para chegar na Versão 1 (MVP: visões Membro, Gestor e Administrador), na ordem em que vamos implementar.

Escopo desta versão: foque no MVP com as três visões (Membro, Gestor, Administrador). Dependente e Consultor ficam para uma etapa de evolução.

Sobre os pontos em aberto do plano, adote estes padrões para o MVP: divisão de despesa por valores definidos por lançamento, com opção de dividir em partes iguais; gráficos só o essencial. Registre essas decisões no docs/arquitetura.md.

Ainda não escreva código de aplicação. Apresente o plano e me deixe aprovar.
```

### Prompt 1 — Infra base (Docker + Django + DRF + Postgres)
```
Monte a base do projeto:
- docker-compose.yml com dois serviços: "db" (PostgreSQL) e "backend" (Django), com o backend esperando o banco subir.
- Projeto Django em backend/, com Django REST Framework instalado e a conexão do PostgreSQL lida por variáveis de ambiente (use .env e .env.example).
- Endpoint de health check em /api/health/ que retorna 200 e um JSON de status.
- requirements.txt com as dependências.

Objetivo: eu rodar `docker compose up` e acessar http://localhost:8000/api/health/ com o Django conectado ao Postgres.

Ao terminar, rode para conferir que sobe, corrija o que faltar e faça commit.
```
*Rode você mesmo o `docker compose up` e teste o /api/health/ antes de seguir.*

### Prompt 2 — Modelo de dados + migrações
```
Implemente o modelo de dados do MVP como models do Django, seguindo docs/arquitetura.md e o @docs/plano.md.

Ponto central: o papel de sistema do usuário é só "comum" ou "admin". Os outros papéis (responsável, membro, dependente, consultor) NÃO ficam no cadastro do usuário — são definidos por relacionamento (MembroGrupo.papel_no_grupo e AutorizacaoConsultor). Use um User customizado (AbstractUser) com o campo papel_sistema e login por e-mail.

Entidades do MVP: Usuario (User custom), Conta, Categoria, Transacao, Grupo, MembroGrupo, Orcamento, DivisaoDespesa. Já deixe também os models de Mesada, AutorizacaoConsultor, ContaAPagar e Recomendacao criados (para a evolução), mas sem endpoints por enquanto.

Inclua validações de integridade no modelo onde fizer sentido (ex.: transação sempre aponta para conta e categoria válidas).

Gere as migrações e rode-as no container. Confira que o banco é criado sem erros e faça commit.
```

### Prompt 3 — Autenticação por token + Django admin
```
Implemente a autenticação com TokenAuthentication do Django REST Framework:
- Endpoint de cadastro de usuário comum.
- Endpoint de login que devolve o token.
- Endpoint para ver o próprio perfil.
- Distinção entre usuário comum e administrador (papel_sistema).

Configure o Django admin e registre as entidades para a visão de Administrador (gestão de usuários e categorias padrão). Documente no README como criar o superusuário.

Rode e teste os fluxos de cadastro e login (curl ou httpie). Faça commit.
```

### Prompt 4 — API CRUD + permissões por visão  *(use plan mode — é o coração do projeto)*
```
Implemente a API CRUD (serializers + viewsets do DRF) para as entidades do MVP e, principalmente, as permissões que isolam cada visão. Esta é a parte mais sensível.

Regras de acesso que precisam valer (todas viram teste depois):
- Cada usuário só acessa as próprias transações, contas e categorias pessoais.
- O Gestor (responsável do grupo) vê o orçamento e os lançamentos do grupo inteiro, mas NÃO as finanças pessoais que um membro não compartilhou.
- O Administrador gerencia usuários e categorias padrão, mas NUNCA acessa o conteúdo financeiro (transações, contas) de ninguém.
- Toda requisição a recurso protegido exige token; sem token, acesso negado.
- Só o responsável administra o grupo (membros, orçamento, metas); membro comum participa mas não administra.

Faça as permissões com classes de permissão do DRF aplicadas por endpoint (fica testável). Apresente o plano das viewsets e permissões antes de implementar. Ao final, rode e faça commit.
```

### Prompt 5 — Regras de negócio: grupo, divisão de despesas, "quem deve a quem"
```
Implemente as regras de negócio do grupo:
- Criar grupo (quem cria vira responsável), convidar/adicionar membros.
- Registrar despesa do grupo e dividi-la entre os participantes, gerando as linhas de DivisaoDespesa. Invariante obrigatória: a soma das partes é sempre igual ao valor total da transação — recuse o registro se não fechar.
- Endpoint que calcula "quem deve a quem" no grupo.
- Orçamento do grupo: previsto x realizado e gasto por categoria.

Suporte divisão por valores definidos por participante e divisão em partes iguais. Rode, confira a invariante da soma na prática e faça commit.
```

### Prompt 6 — Testes automáticos  *(use plan mode — importante para o relatório)*
```
Escreva a suíte de testes automáticos com o framework de testes do Django/DRF, cobrindo os critérios de validação do @docs/plano.md. Organize por tema.

Acesso e isolamento (cada teste simula um tipo de usuário e verifica se o acesso é permitido ou negado):
- Usuário tenta ler transações de outro usuário → negado.
- Administrador tenta abrir transações de um usuário → negado.
- Responsável tenta ver finanças pessoais não compartilhadas de um membro → só aparecem os dados do grupo.
- Requisição sem token a recurso protegido → negado.
- Membro comum tenta administrar o grupo → negado.

Integridade:
- Despesa dividida cuja soma das partes ≠ valor total → recusada.
- Transação apontando para conta ou categoria inexistente → recusada.

CRUD básico de cada entidade (criar, ler, atualizar, remover), respeitando as permissões.

Configure para rodar tudo com um comando dentro do container. Rode a suíte, faça passar e faça commit. Depois, atualize o DEVLOG.md com quais testes pegaram bugs de verdade.
```

### Prompt 7 — Frontend React  *(use plan mode)*
```
Crie o frontend em React (use Vite) em frontend/, consumindo a API do backend.

- Cliente de API que guarda o token e o envia nas requisições; telas de cadastro e login.
- Painel do Membro (minhas finanças): saldo das contas, receitas/despesas por categoria, orçamento pessoal.
- Painel do Gestor: orçamento do grupo (previsto x realizado), gasto por categoria, lançamentos e "quem deve a quem".
- Visão de Administrador: gestão de usuários e categorias padrão (tela simples que consome a API).
- Um ou dois gráficos com Recharts nos painéis.
- Roteamento que mostra a visão certa conforme o usuário logado.

Adicione o serviço "frontend" ao docker-compose para dev. Rode, confira que loga e mostra os painéis e faça commit.
```

### Prompt 8 — Dockerfiles, dados de exemplo e README (empacotar a entrega)
```
Prepare o projeto para entrega e demonstração:
- Dockerfile adequado para o backend e um para o frontend (build + servir). Ajuste o docker-compose para subir db + backend + frontend com um único `docker compose up`.
- Um comando de seed (management command ou fixture) que cria dados de demonstração: usuários (comum e admin), um grupo com responsável e membros, categorias, transações e uma despesa dividida. Isso facilita gravar o vídeo.
- README.md com: o que é o projeto, como subir com Docker, como criar o superusuário, como rodar os testes e um usuário/senha de demonstração.

Confira que, numa pasta limpa, `docker compose up` sobe tudo e a aplicação funciona ponta a ponta. Faça commit.
```

### Prompt 9 — *(Evolução, opcional)* Visão Dependente / mesada
```
Adicione a visão Dependente como evolução, seguindo o plano:
- Mesada com valor, período de recarga e saldo atual; o dependente vê apenas a própria mesada e lança os próprios gastos, sem enxergar o resto do grupo.
- Regra: gasto acima do limite da mesada no período é bloqueado.
- Permissões, endpoints e uma tela simples no frontend.

Testes: dependente não acessa nada além da própria mesada e lançamentos; gasto acima do limite é bloqueado. Rode os testes e faça commit.
```

### Prompt 10 — *(Evolução, opcional)* Visão Consultor
```
Adicione a visão Consultor como evolução, seguindo o plano:
- AutorizacaoConsultor liga consultor a cliente; o consultor só enxerga clientes que o autorizaram, sempre em modo leitura.
- Recomendação: só pode ser criada por um consultor com autorização válida daquele cliente.
- Endpoints, permissões e uma tela simples de carteira de clientes/recomendações.

Testes: consultor tenta acessar cliente que não o autorizou → negado; consultor sem autorização válida tenta gravar recomendação → recusado; consultor tenta alterar dado do cliente → recusado (só leitura). Rode os testes e faça commit.
```

### Prompt 11 — Revisão final e checklist de entrega
```
Revisão final para a entrega da Atividade 04:
- Rode a suíte de testes inteira e garanta que passa.
- Confira que existe Dockerfile e que `docker compose up` sobe tudo do zero.
- Revise o README e o DEVLOG.md.
- Aponte qualquer regra de acesso do plano que ainda não esteja coberta por teste.

Rode /code-review e /security-review nas mudanças e me traga um resumo do que ainda vale ajustar antes de entregar.
```

---

## Para o relatório e o vídeo (exigências da Atividade 04)

- **Relatório:** use o `DEVLOG.md` como matéria-prima. Foquem em onde os agentes aceleraram, onde erraram ou "inventaram" e precisaram de correção, como vocês dividiram o trabalho com o agente e — o ponto que o enunciado pede — **como o plano de testes funcionou na prática** (quais testes pegaram bugs reais, quais regras de acesso foram mais difíceis de garantir).
- **Vídeo (até 10 min):** mostrem a app rodando (cadastro → lançar transação → criar grupo → dividir despesa → "quem deve a quem" nos painéis), passem rápido pelo código (models, permissões, um teste de acesso) e fechem com 2–3 observações do relatório.
