# Validação com o cliente — NossoBolso

O plano (§6) previa validar os critérios de aceitação da versão mínima com um cliente real
(uma família ou república). Como cliente de referência usamos o cenário **Família Silva**,
simulado com os dados de demonstração (`python manage.py seed_demo`), percorrendo os fluxos
principais na interface como faria uma família de verdade.

**Data da sessão:** julho/2026
**Roteiro executado por:** equipe do projeto, alternando entre os papéis (gestor, membro, dependente, consultor, admin)

## Roteiro percorrido e resultados

### 1. Cadastro e login (critério: usuário se cadastra, faz login e se distingue de admin)

| Passo | Resultado |
|---|---|
| Cadastro de novo usuário pela tela de cadastro | OK — entra como `papel_sistema = comum` |
| Login com João (joao@demo.com) | OK — vai para o painel de Membro |
| Login com admin@demo.com | OK — vai direto para o painel de Administrador, sem acesso a finanças |

### 2. Finanças pessoais (critério: contas, categorias e transações pessoais)

| Passo | Resultado |
|---|---|
| João cria uma conta nova ("Vale-refeição") | OK |
| João lança uma despesa de mercado | OK — aparece na lista e no gráfico de pizza |
| João importa um extrato CSV de teste | OK — transações criadas em lote, linhas inválidas reportadas sem abortar a importação |
| Ana tenta ver as transações pessoais de João | OK (negado) — a lista de Ana mostra apenas as próprias transações e as do grupo |

### 3. Grupo e divisão de despesas (critério: grupo com responsável, despesa dividida, quem deve a quem)

| Passo | Resultado |
|---|---|
| João (responsável) abre "Grupos" → Família Silva | OK — membros, transações do grupo, mesadas |
| João registra "Compras do churrasco" (R$ 180) dividida em partes iguais com Ana | OK — divisão 90/90, soma fecha com o total |
| Tela "Quem Deve a Quem" | OK — saldo líquido por membro coerente com as despesas lançadas |
| Ana (membro) tenta adicionar um membro ao grupo | OK (negado) — 403, só o responsável administra |

### 4. Dependente (critério: dependente só vê a própria mesada; limite bloqueado)

| Passo | Resultado |
|---|---|
| Pedro faz login | OK — cai direto no painel de mesada, sem menu de grupos |
| Pedro lança um gasto dentro do saldo | OK — saldo da mesada deduzido na hora |
| Pedro tenta gastar acima do saldo | OK (bloqueado) — mensagem clara com o saldo disponível |
| João recarrega a mesada de Pedro pela aba "Mesadas" | OK — saldo atualizado, gasto passa a ser aceito |

### 5. Consultor (critério: só clientes autorizados, modo leitura; recomendação exige autorização)

| Passo | Resultado |
|---|---|
| Carlos faz login e abre "Consultoria" | OK — carteira mostra João, Maria e Roberto (apenas quem o autorizou) |
| Carlos abre as finanças de João | OK — modo leitura; nenhum botão de edição |
| Carlos deixa recomendação para João (nível comentar) | OK |
| Carlos tenta deixar recomendação para Maria (nível leitura) | OK (negado) — 403 |
| João revoga o Carlos na aba "Consultores" | OK — Carlos deixa de ver João na carteira |

### 6. Administrador (critério: nunca acessa finanças de usuários)

| Passo | Resultado |
|---|---|
| Admin gerencia usuários e categorias padrão | OK |
| Admin tenta acessar `/api/transacoes/` e `/api/contas/` | OK (negado) — 403 |

## Feedback do "cliente" e ajustes decorrentes

1. **"Não sabia como chegar no painel do grupo"** → adicionado o link **Grupos** na barra de navegação
   (antes o painel do gestor só era acessível digitando a URL).
2. **"Quando o gasto do Pedro era bloqueado, não aparecia o motivo"** → mensagens de erro da API agora
   são exibidas nas telas (painéis Membro, Gestor e Dependente).
3. **"Queria autorizar o consultor pelo e-mail, não por número de ID"** → o endpoint de autorização
   passou a aceitar `consultor_email`, e a tela usa e-mail.

## Conclusão

Todos os critérios de aceitação da versão mínima (plano §5) foram verificados na interface com o
cenário simulado, além dos fluxos de evolução (dependente, consultor, contas a pagar, metas).
Fica como ressalva a validação com uma família externa ao grupo, recomendada antes de um uso real.
