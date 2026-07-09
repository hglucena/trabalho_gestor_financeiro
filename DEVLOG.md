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
