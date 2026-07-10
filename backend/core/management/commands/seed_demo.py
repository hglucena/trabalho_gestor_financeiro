import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    AutorizacaoConsultor,
    Categoria,
    Conta,
    ContaAPagar,
    DivisaoDespesa,
    Grupo,
    MembroGrupo,
    Mesada,
    MetaEconomia,
    Orcamento,
    Recomendacao,
    Transacao,
    Usuario,
)

SENHA = "senha123"
MESES_DE_HISTORICO = 6


def meses_atras(data, i):
    """Mesmo dia (limitado a 28), i meses antes."""
    m = data.month - i
    ano = data.year + (m - 1) // 12
    mes = (m - 1) % 12 + 1
    return data.replace(year=ano, month=mes, day=min(data.day, 28))


class Command(BaseCommand):
    help = "Popula o banco com um cenario completo de demonstracao (familias, republica, consultores, 6 meses de historico)"

    def handle(self, *args, **options):
        random.seed(42)  # histórico reprodutível entre execuções
        self.agora = timezone.now()
        self.stdout.write("Criando dados de demonstracao...")

        self._criar_usuarios()
        self._criar_categorias()
        self._criar_contas()
        self._criar_historico_pessoal()
        self._criar_grupos()
        self._criar_mesadas()
        self._criar_consultores()
        self._criar_contas_a_pagar()
        self._criar_metas()
        self._criar_orcamentos()
        self._resumo()

    # ── Usuários ──────────────────────────────────────────────────────
    def _usuario(self, email, nome, papel="comum", staff=False):
        usuario, _ = Usuario.objects.get_or_create(
            email=email,
            defaults={
                "nome": nome,
                "papel_sistema": papel,
                "is_staff": staff,
                "is_superuser": staff,
            },
        )
        usuario.set_password("admin123" if papel == "admin" else SENHA)
        usuario.save()
        return usuario

    def _criar_usuarios(self):
        self.admin = self._usuario("admin@demo.com", "Administrador Demo", "admin", staff=True)

        # Família Silva
        self.joao = self._usuario("joao@demo.com", "Joao Silva")
        self.ana = self._usuario("ana@demo.com", "Ana Silva")
        self.pedro = self._usuario("pedro@demo.com", "Pedro Silva")          # dependente

        # República Central
        self.maria = self._usuario("maria@demo.com", "Maria Oliveira")
        self.lucas = self._usuario("lucas@demo.com", "Lucas Santos")
        self.julia = self._usuario("julia@demo.com", "Julia Costa")

        # Família Costa
        self.roberto = self._usuario("roberto@demo.com", "Roberto Costa")
        self.fernanda = self._usuario("fernanda@demo.com", "Fernanda Costa")
        self.bia = self._usuario("bia@demo.com", "Bia Costa")                # dependente

        # Consultores
        self.carlos = self._usuario("carlos@demo.com", "Carlos Consultor")
        self.paula = self._usuario("paula@demo.com", "Paula Consultora")

        self.stdout.write("  11 usuarios criados (admin, 2 familias, republica, 2 consultores)")

    # ── Categorias ────────────────────────────────────────────────────
    def _criar_categorias(self):
        cats_data = [
            ("Alimentacao", "despesa"), ("Transporte", "despesa"),
            ("Moradia", "despesa"), ("Lazer", "despesa"),
            ("Saude", "despesa"), ("Educacao", "despesa"),
            ("Assinaturas", "despesa"), ("Cartao de Credito", "despesa"),
            ("Contas", "despesa"), ("Poupanca", "despesa"),
            ("Salario", "receita"), ("Freelance", "receita"),
            ("Investimentos", "receita"),
        ]
        self.categorias = {}
        for nome, tipo in cats_data:
            cat, _ = Categoria.objects.get_or_create(
                usuario=None, nome=nome, defaults={"tipo": tipo, "padrao": True},
            )
            self.categorias[nome] = cat
        self.stdout.write(f"  {len(self.categorias)} categorias padrao")

    # ── Contas ────────────────────────────────────────────────────────
    def _conta(self, usuario, nome, saldo):
        conta, _ = Conta.objects.get_or_create(
            usuario=usuario, nome=nome, defaults={"saldo_inicial": Decimal(saldo)},
        )
        return conta

    def _criar_contas(self):
        self.contas = {
            self.joao: self._conta(self.joao, "Conta Corrente", "5000.00"),
            self.ana: self._conta(self.ana, "Conta Corrente", "3200.00"),
            self.pedro: self._conta(self.pedro, "Carteira", "0.00"),
            self.maria: self._conta(self.maria, "Carteira Digital", "2800.00"),
            self.lucas: self._conta(self.lucas, "Conta Corrente", "1500.00"),
            self.julia: self._conta(self.julia, "Conta Corrente", "2100.00"),
            self.roberto: self._conta(self.roberto, "Conta Corrente", "8000.00"),
            self.fernanda: self._conta(self.fernanda, "Conta Corrente", "4500.00"),
            self.bia: self._conta(self.bia, "Carteira", "0.00"),
        }
        self._conta(self.joao, "Poupanca", "10000.00")
        self._conta(self.roberto, "Investimentos", "25000.00")
        self.stdout.write("  Contas criadas")

    # ── Histórico pessoal (6 meses, para os gráficos) ─────────────────
    def _transacao(self, usuario, categoria, tipo, valor, descricao, data, grupo=None):
        return Transacao.objects.create(
            usuario=usuario, conta=self.contas[usuario], categoria=categoria,
            tipo=tipo, valor=Decimal(str(round(valor, 2))),
            descricao=descricao, data=data, grupo=grupo,
        )

    def _criar_historico_pessoal(self):
        if Transacao.objects.filter(usuario=self.joao).exists():
            self.stdout.write("  Historico ja existe — pulando transacoes")
            return

        perfis = [
            # (usuario, salário, gastos mensais: (categoria, descrição, base))
            (self.joao, 7000, [
                ("Alimentacao", "Supermercado", 850), ("Transporte", "Combustivel", 320),
                ("Lazer", "Cinema e passeios", 180), ("Saude", "Plano de saude", 420),
                ("Assinaturas", "Streaming", 65), ("Cartao de Credito", "Fatura do cartao", 1250),
            ]),
            (self.ana, 5200, [
                ("Alimentacao", "Feira e mercado", 600), ("Transporte", "Aplicativo", 240),
                ("Educacao", "Curso de ingles", 350), ("Lazer", "Restaurantes", 220),
            ]),
            (self.maria, 4500, [
                ("Alimentacao", "Mercado", 520), ("Transporte", "Onibus e metro", 180),
                ("Lazer", "Shows", 150), ("Assinaturas", "Streaming e musica", 55),
                ("Cartao de Credito", "Fatura do cartao", 780),
            ]),
            (self.lucas, 3800, [
                ("Alimentacao", "Mercado", 480), ("Transporte", "Bicicleta/app", 90),
                ("Educacao", "Faculdade", 650), ("Lazer", "Games", 120),
            ]),
            (self.julia, 4100, [
                ("Alimentacao", "Mercado", 510), ("Saude", "Academia", 130),
                ("Lazer", "Viagens curtas", 260),
            ]),
            (self.roberto, 12000, [
                ("Alimentacao", "Supermercado", 1400), ("Transporte", "Combustivel", 550),
                ("Educacao", "Escola da Bia", 1800), ("Saude", "Plano familiar", 950),
                ("Lazer", "Clube", 400), ("Assinaturas", "TV e streaming", 120),
                ("Cartao de Credito", "Fatura do cartao", 2300),
            ]),
            (self.fernanda, 6800, [
                ("Alimentacao", "Feira organica", 700), ("Transporte", "Combustivel", 380),
                ("Saude", "Terapia", 480), ("Lazer", "Livros e cafes", 190),
            ]),
        ]

        total = 0
        for usuario, salario, gastos in perfis:
            for i in range(MESES_DE_HISTORICO - 1, -1, -1):
                mes = meses_atras(self.agora, i)
                dia_pgto = mes.replace(day=5)
                self._transacao(usuario, self.categorias["Salario"], "receita",
                                salario, "Salario mensal", dia_pgto)
                if usuario in (self.joao, self.fernanda) and i % 2 == 0:
                    self._transacao(usuario, self.categorias["Freelance"], "receita",
                                    salario * 0.12 * random.uniform(0.7, 1.3),
                                    "Trabalho extra", mes.replace(day=18))
                for nome_cat, descricao, base in gastos:
                    valor = base * random.uniform(0.8, 1.25)
                    dia = mes.replace(day=random.randint(6, 27))
                    self._transacao(usuario, self.categorias[nome_cat], "despesa",
                                    valor, descricao, dia)
                    total += 1
        self.stdout.write(f"  Historico pessoal de {MESES_DE_HISTORICO} meses criado ({total}+ transacoes)")

    # ── Grupos com despesas divididas mensais ─────────────────────────
    def _grupo(self, nome, descricao, responsavel, membros, dependentes=()):
        grupo, _ = Grupo.objects.get_or_create(
            nome=nome, defaults={"descricao": descricao, "responsavel": responsavel},
        )
        MembroGrupo.objects.get_or_create(
            grupo=grupo, usuario=responsavel, defaults={"papel_no_grupo": "responsavel"},
        )
        for m in membros:
            MembroGrupo.objects.get_or_create(
                grupo=grupo, usuario=m, defaults={"papel_no_grupo": "membro"},
            )
        for d in dependentes:
            MembroGrupo.objects.get_or_create(
                grupo=grupo, usuario=d, defaults={"papel_no_grupo": "dependente"},
            )
        return grupo

    def _despesa_dividida(self, grupo, pagador, participantes, categoria, valor, descricao, data):
        transacao = self._transacao(pagador, categoria, "despesa", valor, descricao, data, grupo=grupo)
        parte = round(valor / len(participantes), 2)
        ajuste = round(valor - parte * len(participantes), 2)
        for i, participante in enumerate(participantes):
            DivisaoDespesa.objects.create(
                transacao=transacao, participante=participante,
                valor_devido=Decimal(str(parte + (ajuste if i == 0 else 0))),
                pago=(participante == pagador),
            )

    def _criar_grupos(self):
        self.grupo_silva = self._grupo(
            "Familia Silva", "Despesas da casa dos Silva",
            self.joao, [self.ana], [self.pedro],
        )
        self.grupo_republica = self._grupo(
            "Republica Central", "Despesas compartilhadas da republica",
            self.maria, [self.lucas, self.julia],
        )
        self.grupo_costa = self._grupo(
            "Familia Costa", "Orcamento da familia Costa",
            self.roberto, [self.fernanda], [self.bia],
        )

        if Transacao.objects.filter(grupo=self.grupo_silva).exists():
            self.stdout.write("  Despesas de grupo ja existem — pulando")
            return

        for i in range(3, -1, -1):
            mes = meses_atras(self.agora, i)
            # Família Silva: João paga, divide com Ana
            self._despesa_dividida(self.grupo_silva, self.joao, [self.joao, self.ana],
                                   self.categorias["Moradia"], 2200, "Aluguel + condominio",
                                   mes.replace(day=10))
            self._despesa_dividida(self.grupo_silva, self.ana, [self.joao, self.ana],
                                   self.categorias["Alimentacao"],
                                   900 * random.uniform(0.85, 1.15),
                                   "Compras do mes", mes.replace(day=15))
            # República: 3 moradores
            moradores = [self.maria, self.lucas, self.julia]
            self._despesa_dividida(self.grupo_republica, self.maria, moradores,
                                   self.categorias["Moradia"], 1800, "Aluguel da republica",
                                   mes.replace(day=8))
            self._despesa_dividida(self.grupo_republica, self.lucas, moradores,
                                   self.categorias["Alimentacao"],
                                   600 * random.uniform(0.8, 1.2),
                                   "Compras coletivas", mes.replace(day=12))
            self._despesa_dividida(self.grupo_republica, self.julia, moradores,
                                   self.categorias["Assinaturas"], 89.90,
                                   "Internet da casa", mes.replace(day=20))
            # Família Costa
            self._despesa_dividida(self.grupo_costa, self.roberto, [self.roberto, self.fernanda],
                                   self.categorias["Moradia"], 3500, "Financiamento da casa",
                                   mes.replace(day=7))
            self._despesa_dividida(self.grupo_costa, self.fernanda, [self.roberto, self.fernanda],
                                   self.categorias["Lazer"],
                                   450 * random.uniform(0.7, 1.3),
                                   "Passeios em familia", mes.replace(day=22))

        self.stdout.write("  3 grupos com 4 meses de despesas divididas")

    # ── Mesadas dos dependentes ───────────────────────────────────────
    def _criar_mesadas(self):
        mesada_pedro, criada = Mesada.objects.get_or_create(
            dependente=self.pedro, grupo=self.grupo_silva,
            defaults={"valor": Decimal("200.00"), "periodo_recarga": "mensal",
                      "saldo_atual": Decimal("200.00")},
        )
        if criada:
            gastos = [("Lanche na escola", 12.50), ("Figurinhas", 8.00), ("Cinema", 35.00)]
            for descricao, valor in gastos:
                self._transacao(self.pedro, self.categorias["Lazer"], "despesa",
                                valor, descricao,
                                self.agora - timedelta(days=random.randint(1, 20)))
                mesada_pedro.saldo_atual -= Decimal(str(valor))
            mesada_pedro.save()

        mesada_bia, criada = Mesada.objects.get_or_create(
            dependente=self.bia, grupo=self.grupo_costa,
            defaults={"valor": Decimal("80.00"), "periodo_recarga": "semanal",
                      "saldo_atual": Decimal("80.00")},
        )
        if criada:
            for descricao, valor in [("Sorvete", 15.00), ("Papelaria", 22.90)]:
                self._transacao(self.bia, self.categorias["Lazer"], "despesa",
                                valor, descricao,
                                self.agora - timedelta(days=random.randint(1, 6)))
                mesada_bia.saldo_atual -= Decimal(str(valor))
            mesada_bia.save()

        self.stdout.write("  Mesadas de Pedro (mensal) e Bia (semanal) com gastos")

    # ── Consultores com carteiras de clientes ─────────────────────────
    def _criar_consultores(self):
        carteiras = [
            (self.carlos, [
                (self.joao, "comentar"), (self.maria, "leitura"), (self.roberto, "comentar"),
            ]),
            (self.paula, [
                (self.fernanda, "comentar"), (self.lucas, "leitura"),
            ]),
        ]
        for consultor, clientes in carteiras:
            for cliente, nivel in clientes:
                AutorizacaoConsultor.objects.get_or_create(
                    consultor=consultor, cliente=cliente,
                    defaults={"nivel": nivel, "status": True},
                )

        recomendacoes = [
            (self.carlos, self.joao,
             "Seus gastos com alimentacao cresceram nos ultimos meses. "
             "Considere definir um teto de R$ 900 e revisar as compras semanais."),
            (self.carlos, self.joao,
             "Otimo trabalho com a reserva de emergencia — mantenha os aportes mensais."),
            (self.carlos, self.roberto,
             "A parcela de educacao pesa 15% da renda. Vale pesquisar bolsas ou "
             "renegociar a mensalidade no proximo ciclo."),
            (self.paula, self.fernanda,
             "Sugiro migrar parte do saldo parado da conta corrente para um CDB "
             "com liquidez diaria."),
        ]
        for consultor, cliente, texto in recomendacoes:
            Recomendacao.objects.get_or_create(
                consultor=consultor, cliente=cliente, texto=texto,
                defaults={"data": self.agora - timedelta(days=random.randint(1, 30))},
            )
        self.stdout.write("  2 consultores: Carlos (3 clientes) e Paula (2 clientes), com recomendacoes")

    # ── Contas a pagar ────────────────────────────────────────────────
    def _criar_contas_a_pagar(self):
        hoje = self.agora.date()
        contas = [
            (self.joao, "Aluguel", "2200.00", 5, True, False),
            (self.joao, "Internet", "99.90", 2, True, False),
            (self.joao, "IPVA parcela 3", "450.00", 20, False, False),
            (self.joao, "Cartao de credito", "1350.00", -3, True, True),
            (self.maria, "Aluguel da republica", "1800.00", 8, True, False),
            (self.maria, "Energia", "210.00", 4, True, False),
            (self.roberto, "Financiamento", "3500.00", 7, True, False),
            (self.roberto, "Escola da Bia", "1800.00", 10, True, False),
            (self.fernanda, "Seguro do carro", "320.00", 15, True, False),
        ]
        for usuario, descricao, valor, dias, recorrente, pago in contas:
            ContaAPagar.objects.get_or_create(
                usuario=usuario, descricao=descricao,
                defaults={
                    "valor": Decimal(valor),
                    "vencimento": hoje + timedelta(days=dias),
                    "recorrencia": recorrente,
                    "pago": pago,
                },
            )
        self.stdout.write("  Contas a pagar criadas (incluindo vencidas e pagas)")

    # ── Metas de economia ─────────────────────────────────────────────
    def _criar_metas(self):
        hoje = self.agora.date()
        metas = [
            (self.joao, "Reserva de emergencia", "10000.00", "3500.00", None),
            (self.joao, "Trocar de carro", "45000.00", "12000.00", hoje + timedelta(days=540)),
            (self.maria, "Viagem de ferias", "4000.00", "1200.00", hoje + timedelta(days=180)),
            (self.lucas, "Notebook novo", "5500.00", "4900.00", hoje + timedelta(days=60)),
            (self.julia, "Intercambio", "20000.00", "2500.00", hoje + timedelta(days=720)),
            (self.fernanda, "Reforma da cozinha", "15000.00", "15000.00", None),  # concluída
            (self.pedro, "PS5", "3800.00", "250.00", None),
            (self.bia, "Bicicleta", "600.00", "120.00", None),
        ]
        for usuario, nome, alvo, atual, prazo in metas:
            MetaEconomia.objects.get_or_create(
                usuario=usuario, nome=nome,
                defaults={"valor_alvo": Decimal(alvo), "valor_atual": Decimal(atual),
                          "prazo": prazo},
            )
        self.stdout.write("  Metas de economia criadas (incluindo uma concluida)")

    # ── Orçamentos ────────────────────────────────────────────────────
    def _criar_orcamentos(self):
        hoje = self.agora.date().replace(day=1)
        orcamentos_pessoais = [
            (self.joao, "Alimentacao", "900.00"),
            (self.joao, "Lazer", "250.00"),
            (self.maria, "Alimentacao", "600.00"),
            (self.roberto, "Lazer", "500.00"),
            (self.fernanda, "Saude", "600.00"),
        ]
        for usuario, cat, limite in orcamentos_pessoais:
            Orcamento.objects.get_or_create(
                usuario=usuario, categoria=self.categorias[cat],
                defaults={"valor_limite": Decimal(limite), "periodo": hoje},
            )

        orcamentos_grupo = [
            (self.grupo_silva, "Moradia", "2500.00"),
            (self.grupo_silva, "Alimentacao", "1000.00"),
            (self.grupo_republica, "Moradia", "1900.00"),
            (self.grupo_republica, "Alimentacao", "700.00"),
            (self.grupo_republica, "Assinaturas", "100.00"),
            (self.grupo_costa, "Moradia", "3600.00"),
            (self.grupo_costa, "Lazer", "400.00"),
        ]
        for grupo, cat, limite in orcamentos_grupo:
            Orcamento.objects.get_or_create(
                grupo=grupo, categoria=self.categorias[cat],
                defaults={"valor_limite": Decimal(limite), "periodo": hoje},
            )
        self.stdout.write("  Orcamentos pessoais e dos 3 grupos criados")

    # ── Resumo ────────────────────────────────────────────────────────
    def _resumo(self):
        self.stdout.write(self.style.SUCCESS(
            "\n=== Dados de demonstracao prontos! ===\n"
            "Login: http://localhost:5173/login (senha de todos: senha123)\n\n"
            "  Familia Silva\n"
            "    joao@demo.com     — gestor do grupo, cliente do Carlos\n"
            "    ana@demo.com      — membro\n"
            "    pedro@demo.com    — dependente (mesada mensal R$ 200)\n\n"
            "  Republica Central\n"
            "    maria@demo.com    — gestora, cliente do Carlos (leitura)\n"
            "    lucas@demo.com    — membro, cliente da Paula (leitura)\n"
            "    julia@demo.com    — membro\n\n"
            "  Familia Costa\n"
            "    roberto@demo.com  — gestor, cliente do Carlos\n"
            "    fernanda@demo.com — membro, cliente da Paula\n"
            "    bia@demo.com      — dependente (mesada semanal R$ 80)\n\n"
            "  Consultores\n"
            "    carlos@demo.com   — 3 clientes (Joao, Maria, Roberto)\n"
            "    paula@demo.com    — 2 clientes (Fernanda, Lucas)\n\n"
            "  Admin: admin@demo.com / admin123\n"
        ))
