from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    Categoria,
    Conta,
    ContaAPagar,
    Mesada,
    MetaEconomia,
    Orcamento,
    Transacao,
    Usuario,
)


class ExtrasTestCase(APITestCase):
    """Base comum: dois usuários comuns e um admin, com tokens."""

    def setUp(self):
        self.joao = Usuario.objects.create_user("joao@test.com", "Joao", "senha123")
        self.maria = Usuario.objects.create_user("maria@test.com", "Maria", "senha123")
        self.admin = Usuario.objects.create_superuser("admin@test.com", "Admin", "senha123")

        self.token_joao = self._login("joao@test.com")
        self.token_maria = self._login("maria@test.com")
        self.token_admin = self._login("admin@test.com")

        self.conta_joao = Conta.objects.create(usuario=self.joao, nome="Carteira Joao")
        self.cat_alimentacao = Categoria.objects.create(
            usuario=None, nome="Alimentacao", tipo="despesa", padrao=True
        )

    def _login(self, email):
        response = self.client.post("/api/login/", {"username": email, "password": "senha123"})
        return response.data["token"]

    def _como(self, token):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)


# ══════════════════════════════════════════════════════════════════════════
# Contas a pagar
# ══════════════════════════════════════════════════════════════════════════

class ContaAPagarTests(ExtrasTestCase):
    def test_usuario_cria_conta_a_pagar(self):
        self._como(self.token_joao)
        response = self.client.post("/api/contas-a-pagar/", {
            "descricao": "Aluguel", "valor": "800.00", "vencimento": "2026-08-05",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["descricao"], "Aluguel")
        self.assertFalse(response.data["pago"])

    def test_usuario_so_ve_proprias_contas_a_pagar(self):
        ContaAPagar.objects.create(usuario=self.joao, descricao="Luz", valor=120, vencimento="2026-08-10")
        ContaAPagar.objects.create(usuario=self.maria, descricao="Agua", valor=80, vencimento="2026-08-10")
        self._como(self.token_joao)
        response = self.client.get("/api/contas-a-pagar/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["descricao"], "Luz")

    def test_usuario_nao_edita_conta_a_pagar_de_outro(self):
        conta = ContaAPagar.objects.create(usuario=self.maria, descricao="Agua", valor=80, vencimento="2026-08-10")
        self._como(self.token_joao)
        response = self.client.patch(f"/api/contas-a-pagar/{conta.id}/", {"pago": True})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_marcar_como_paga(self):
        conta = ContaAPagar.objects.create(usuario=self.joao, descricao="Luz", valor=120, vencimento="2026-08-10")
        self._como(self.token_joao)
        response = self.client.patch(f"/api/contas-a-pagar/{conta.id}/", {"pago": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["pago"])

    def test_filtro_por_pago(self):
        ContaAPagar.objects.create(usuario=self.joao, descricao="Luz", valor=120, vencimento="2026-08-10", pago=True)
        ContaAPagar.objects.create(usuario=self.joao, descricao="Agua", valor=80, vencimento="2026-08-10")
        self._como(self.token_joao)
        response = self.client.get("/api/contas-a-pagar/?pago=false")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["descricao"], "Agua")

    def test_admin_nao_acessa_contas_a_pagar(self):
        self._como(self.token_admin)
        response = self.client.get("/api/contas-a-pagar/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ══════════════════════════════════════════════════════════════════════════
# Recarga de mesada
# ══════════════════════════════════════════════════════════════════════════

class RecargaMesadaTests(ExtrasTestCase):
    def setUp(self):
        super().setUp()
        self.dependente = Usuario.objects.create_user("dep@test.com", "Dep", "senha123")
        self.token_dep = self._login("dep@test.com")
        self._como(self.token_joao)
        r = self.client.post("/api/grupos/", {"nome": "Familia"})
        self.grupo_id = r.data["id"]
        self.client.post(f"/api/grupos/{self.grupo_id}/membros/", {
            "usuario": self.dependente.id, "papel_no_grupo": "dependente",
        })
        self.mesada = Mesada.objects.create(
            dependente=self.dependente, grupo_id=self.grupo_id,
            valor=200, periodo_recarga="mensal", saldo_atual=50,
        )

    def test_gestor_recarrega_valor_padrao(self):
        self._como(self.token_joao)
        response = self.client.post(f"/api/mesadas/{self.mesada.id}/recarregar/", {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data["saldo_atual"]), 250.00)

    def test_gestor_recarrega_valor_custom(self):
        self._como(self.token_joao)
        response = self.client.post(f"/api/mesadas/{self.mesada.id}/recarregar/", {"valor": "30.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data["saldo_atual"]), 80.00)

    def test_dependente_nao_recarrega_propria_mesada(self):
        self._como(self.token_dep)
        response = self.client.post(f"/api/mesadas/{self.mesada.id}/recarregar/", {"valor": "500.00"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recarga_negativa_recusada(self):
        self._como(self.token_joao)
        response = self.client.post(f"/api/mesadas/{self.mesada.id}/recarregar/", {"valor": "-10.00"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_recarga_libera_gasto_bloqueado(self):
        conta_dep = Conta.objects.create(usuario=self.dependente, nome="Carteira Dep")
        self._como(self.token_dep)
        response = self.client.post("/api/transacoes/", {
            "conta": conta_dep.id, "categoria": self.cat_alimentacao.id,
            "tipo": "despesa", "valor": "100.00", "descricao": "Compra",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self._como(self.token_joao)
        self.client.post(f"/api/mesadas/{self.mesada.id}/recarregar/", {})
        self._como(self.token_dep)
        response = self.client.post("/api/transacoes/", {
            "conta": conta_dep.id, "categoria": self.cat_alimentacao.id,
            "tipo": "despesa", "valor": "100.00", "descricao": "Compra",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# ══════════════════════════════════════════════════════════════════════════
# Recarga automática de mesada
# ══════════════════════════════════════════════════════════════════════════

class RecargaAutomaticaTests(ExtrasTestCase):
    def setUp(self):
        super().setUp()
        from datetime import timedelta
        from django.utils import timezone
        self.dependente = Usuario.objects.create_user("depauto@test.com", "DepAuto", "senha123")
        self.token_dep = self._login("depauto@test.com")
        self._como(self.token_joao)
        r = self.client.post("/api/grupos/", {"nome": "Familia Auto"})
        self.grupo_id = r.data["id"]
        self.client.post(f"/api/grupos/{self.grupo_id}/membros/", {
            "usuario": self.dependente.id, "papel_no_grupo": "dependente",
        })
        # mesada semanal cuja última recarga foi há 8 dias — recarga vencida
        self.mesada = Mesada.objects.create(
            dependente=self.dependente, grupo_id=self.grupo_id,
            valor=100, periodo_recarga="semanal", saldo_atual=10,
            ultima_recarga=timezone.now() - timedelta(days=8),
        )

    def test_consulta_aplica_recarga_vencida(self):
        self._como(self.token_dep)
        response = self.client.get("/api/mesadas/")
        self.assertEqual(float(response.data["results"][0]["saldo_atual"]), 110.00)

    def test_dois_periodos_vencidos_recarregam_duas_vezes(self):
        from datetime import timedelta
        from django.utils import timezone
        self.mesada.ultima_recarga = timezone.now() - timedelta(days=15)
        self.mesada.save(update_fields=["ultima_recarga"])
        self._como(self.token_dep)
        response = self.client.get("/api/mesadas/")
        self.assertEqual(float(response.data["results"][0]["saldo_atual"]), 210.00)

    def test_gasto_bloqueado_passa_apos_recarga_automatica(self):
        conta = Conta.objects.create(usuario=self.dependente, nome="Carteira")
        self._como(self.token_dep)
        # saldo era 10, gasto de 50 só passa porque a recarga vencida credita +100
        response = self.client.post("/api/transacoes/", {
            "conta": conta.id, "categoria": self.cat_alimentacao.id,
            "tipo": "despesa", "valor": "50.00", "descricao": "Lanche",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.mesada.refresh_from_db()
        self.assertEqual(float(self.mesada.saldo_atual), 60.00)

    def test_periodo_nao_vencido_nao_recarrega(self):
        from django.utils import timezone
        self.mesada.ultima_recarga = timezone.now()
        self.mesada.save(update_fields=["ultima_recarga"])
        self._como(self.token_dep)
        response = self.client.get("/api/mesadas/")
        self.assertEqual(float(response.data["results"][0]["saldo_atual"]), 10.00)

    def test_comando_recarrega_em_lote(self):
        call_command("recarregar_mesadas")
        self.mesada.refresh_from_db()
        self.assertEqual(float(self.mesada.saldo_atual), 110.00)


# ══════════════════════════════════════════════════════════════════════════
# Metas de economia
# ══════════════════════════════════════════════════════════════════════════

class MetaEconomiaTests(ExtrasTestCase):
    def test_usuario_cria_meta(self):
        self._como(self.token_joao)
        response = self.client.post("/api/metas/", {
            "nome": "Viagem", "valor_alvo": "3000.00", "prazo": "2026-12-31",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data["valor_atual"]), 0.0)
        self.assertFalse(response.data["concluida"])

    def test_valor_alvo_zero_recusado(self):
        self._como(self.token_joao)
        response = self.client.post("/api/metas/", {"nome": "Nada", "valor_alvo": "0.00"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_aporte_soma_e_calcula_percentual(self):
        meta = MetaEconomia.objects.create(usuario=self.joao, nome="Reserva", valor_alvo=1000)
        self._como(self.token_joao)
        response = self.client.post(f"/api/metas/{meta.id}/aportar/", {"valor": "250.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(float(response.data["valor_atual"]), 250.00)
        self.assertEqual(response.data["percentual"], 25.0)

    def test_aporte_negativo_recusado(self):
        meta = MetaEconomia.objects.create(usuario=self.joao, nome="Reserva", valor_alvo=1000)
        self._como(self.token_joao)
        response = self.client.post(f"/api/metas/{meta.id}/aportar/", {"valor": "-50.00"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_meta_concluida_ao_atingir_alvo(self):
        meta = MetaEconomia.objects.create(usuario=self.joao, nome="Reserva", valor_alvo=100, valor_atual=90)
        self._como(self.token_joao)
        response = self.client.post(f"/api/metas/{meta.id}/aportar/", {"valor": "10.00"})
        self.assertTrue(response.data["concluida"])
        self.assertEqual(response.data["percentual"], 100.0)

    def test_usuario_nao_ve_meta_de_outro(self):
        MetaEconomia.objects.create(usuario=self.maria, nome="Dela", valor_alvo=500)
        self._como(self.token_joao)
        response = self.client.get("/api/metas/")
        self.assertEqual(response.data["count"], 0)

    def test_usuario_nao_aporta_na_meta_de_outro(self):
        meta = MetaEconomia.objects.create(usuario=self.maria, nome="Dela", valor_alvo=500)
        self._como(self.token_joao)
        response = self.client.post(f"/api/metas/{meta.id}/aportar/", {"valor": "10.00"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ══════════════════════════════════════════════════════════════════════════
# Importação de extrato CSV
# ══════════════════════════════════════════════════════════════════════════

class ImportacaoCSVTests(ExtrasTestCase):
    def _csv(self, conteudo):
        return SimpleUploadedFile("extrato.csv", conteudo.encode("utf-8"), content_type="text/csv")

    def test_importa_linhas_validas(self):
        csv = (
            "data,descricao,valor,tipo,categoria\n"
            "2026-07-01,Mercado,150.50,despesa,Alimentacao\n"
            "02/07/2026,Salario,\"3000,00\",receita,Salario\n"
        )
        self._como(self.token_joao)
        response = self.client.post("/api/transacoes/importar_csv/", {
            "arquivo": self._csv(csv), "conta": self.conta_joao.id,
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["importadas"], 2)
        self.assertEqual(response.data["erros"], [])
        self.assertEqual(Transacao.objects.filter(usuario=self.joao).count(), 2)

    def test_linha_invalida_vira_erro_sem_abortar(self):
        csv = (
            "data,descricao,valor,tipo,categoria\n"
            "2026-07-01,Mercado,150.50,despesa,Alimentacao\n"
            "data-ruim,Erro,abc,despesa,Alimentacao\n"
        )
        self._como(self.token_joao)
        response = self.client.post("/api/transacoes/importar_csv/", {
            "arquivo": self._csv(csv), "conta": self.conta_joao.id,
        }, format="multipart")
        self.assertEqual(response.data["importadas"], 1)
        self.assertEqual(len(response.data["erros"]), 1)
        self.assertEqual(response.data["erros"][0]["linha"], 3)

    def test_categoria_inexistente_e_criada_para_o_usuario(self):
        csv = "data,descricao,valor,tipo,categoria\n2026-07-01,Cinema,40.00,despesa,Lazer\n"
        self._como(self.token_joao)
        self.client.post("/api/transacoes/importar_csv/", {
            "arquivo": self._csv(csv), "conta": self.conta_joao.id,
        }, format="multipart")
        self.assertTrue(Categoria.objects.filter(usuario=self.joao, nome="Lazer").exists())

    def test_conta_de_outro_usuario_recusada(self):
        conta_maria = Conta.objects.create(usuario=self.maria, nome="Conta Maria")
        csv = "data,descricao,valor,tipo,categoria\n2026-07-01,Mercado,10.00,despesa,Alimentacao\n"
        self._como(self.token_joao)
        response = self.client.post("/api/transacoes/importar_csv/", {
            "arquivo": self._csv(csv), "conta": conta_maria.id,
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sem_arquivo_recusado(self):
        self._como(self.token_joao)
        response = self.client.post("/api/transacoes/importar_csv/", {
            "conta": self.conta_joao.id,
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dependente_nao_importa(self):
        dependente = Usuario.objects.create_user("dep2@test.com", "Dep2", "senha123")
        token_dep = self._login("dep2@test.com")
        self._como(self.token_joao)
        r = self.client.post("/api/grupos/", {"nome": "Familia"})
        self.client.post(f"/api/grupos/{r.data['id']}/membros/", {
            "usuario": dependente.id, "papel_no_grupo": "dependente",
        })
        conta_dep = Conta.objects.create(usuario=dependente, nome="Carteira")
        csv = "data,descricao,valor,tipo,categoria\n2026-07-01,Doce,5.00,despesa,Alimentacao\n"
        self._como(token_dep)
        response = self.client.post("/api/transacoes/importar_csv/", {
            "arquivo": self._csv(csv), "conta": conta_dep.id,
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ══════════════════════════════════════════════════════════════════════════
# Filtros de transações
# ══════════════════════════════════════════════════════════════════════════

class FiltroTransacoesTests(ExtrasTestCase):
    def setUp(self):
        super().setUp()
        self.cat_lazer = Categoria.objects.create(usuario=self.joao, nome="Lazer", tipo="despesa")
        Transacao.objects.create(
            usuario=self.joao, conta=self.conta_joao, categoria=self.cat_alimentacao,
            tipo="despesa", valor=100, descricao="Mercado", data="2026-06-15T12:00:00-03:00",
        )
        Transacao.objects.create(
            usuario=self.joao, conta=self.conta_joao, categoria=self.cat_lazer,
            tipo="despesa", valor=50, descricao="Cinema", data="2026-07-05T12:00:00-03:00",
        )
        Transacao.objects.create(
            usuario=self.joao, conta=self.conta_joao, categoria=self.cat_alimentacao,
            tipo="receita", valor=2000, descricao="Salario", data="2026-07-01T12:00:00-03:00",
        )

    def test_filtro_por_periodo(self):
        self._como(self.token_joao)
        response = self.client.get("/api/transacoes/?data_inicio=2026-07-01&data_fim=2026-07-31")
        self.assertEqual(response.data["count"], 2)

    def test_filtro_por_categoria(self):
        self._como(self.token_joao)
        response = self.client.get(f"/api/transacoes/?categoria={self.cat_lazer.id}")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["descricao"], "Cinema")

    def test_filtro_por_tipo(self):
        self._como(self.token_joao)
        response = self.client.get("/api/transacoes/?tipo=receita")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["descricao"], "Salario")

    def test_filtro_combinado(self):
        self._como(self.token_joao)
        response = self.client.get("/api/transacoes/?tipo=despesa&data_inicio=2026-07-01")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["descricao"], "Cinema")

    def test_data_invalida_ignorada(self):
        self._como(self.token_joao)
        response = self.client.get("/api/transacoes/?data_inicio=nao-e-data")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)


# ══════════════════════════════════════════════════════════════════════════
# Saldo vivo — transações, pagamento de contas e aportes mexem no saldo
# ══════════════════════════════════════════════════════════════════════════

class SaldoVivoTests(ExtrasTestCase):
    def test_saldo_atual_reflete_transacoes(self):
        conta = Conta.objects.create(usuario=self.joao, nome="Corrente", saldo_inicial=1000)
        cat_receita = Categoria.objects.create(usuario=None, nome="Salario", tipo="receita", padrao=True)
        Transacao.objects.create(usuario=self.joao, conta=conta, categoria=cat_receita,
                                 tipo="receita", valor=500, descricao="Salario")
        Transacao.objects.create(usuario=self.joao, conta=conta, categoria=self.cat_alimentacao,
                                 tipo="despesa", valor=200, descricao="Mercado")
        self._como(self.token_joao)
        response = self.client.get("/api/contas/")
        conta_data = next(c for c in response.data["results"] if c["id"] == conta.id)
        self.assertEqual(float(conta_data["saldo_atual"]), 1300.00)

    def test_saldo_pode_ficar_negativo(self):
        self._como(self.token_joao)
        response = self.client.post("/api/transacoes/", {
            "conta": self.conta_joao.id, "categoria": self.cat_alimentacao.id,
            "tipo": "despesa", "valor": "150.00", "descricao": "Gasto no cheque especial",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get("/api/contas/")
        conta_data = next(c for c in response.data["results"] if c["id"] == self.conta_joao.id)
        self.assertEqual(float(conta_data["saldo_atual"]), -150.00)

    def test_pagar_conta_lanca_despesa_e_reduz_saldo(self):
        conta = ContaAPagar.objects.create(usuario=self.joao, descricao="Internet",
                                           valor=120, vencimento="2026-08-10")
        self._como(self.token_joao)
        response = self.client.post(f"/api/contas-a-pagar/{conta.id}/pagar/", {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["pago"])
        self.assertTrue(Transacao.objects.filter(
            usuario=self.joao, descricao="Pagamento: Internet", valor=120, tipo="despesa",
        ).exists())
        r = self.client.get("/api/contas/")
        conta_data = next(c for c in r.data["results"] if c["id"] == self.conta_joao.id)
        self.assertEqual(float(conta_data["saldo_atual"]), -120.00)

    def test_pagar_duas_vezes_recusado(self):
        conta = ContaAPagar.objects.create(usuario=self.joao, descricao="Internet",
                                           valor=120, vencimento="2026-08-10")
        self._como(self.token_joao)
        self.client.post(f"/api/contas-a-pagar/{conta.id}/pagar/", {})
        response = self.client.post(f"/api/contas-a-pagar/{conta.id}/pagar/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Transacao.objects.filter(descricao="Pagamento: Internet").count(), 1)

    def test_aporte_lanca_despesa_e_reduz_saldo(self):
        meta = MetaEconomia.objects.create(usuario=self.joao, nome="Reserva", valor_alvo=1000)
        self._como(self.token_joao)
        response = self.client.post(f"/api/metas/{meta.id}/aportar/", {"valor": "50.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Transacao.objects.filter(
            usuario=self.joao, descricao="Aporte na meta: Reserva", valor=50,
        ).exists())
        r = self.client.get("/api/contas/")
        conta_data = next(c for c in r.data["results"] if c["id"] == self.conta_joao.id)
        self.assertEqual(float(conta_data["saldo_atual"]), -50.00)


class MetaDependenteTests(ExtrasTestCase):
    """Dependente cria meta (ex.: PS5) e guarda dinheiro DA MESADA nela."""

    def setUp(self):
        super().setUp()
        self.dependente = Usuario.objects.create_user("depmeta@test.com", "DepMeta", "senha123")
        self.token_dep = self._login("depmeta@test.com")
        self._como(self.token_joao)
        r = self.client.post("/api/grupos/", {"nome": "Familia Meta"})
        self.client.post(f"/api/grupos/{r.data['id']}/membros/", {
            "usuario": self.dependente.id, "papel_no_grupo": "dependente",
        })
        self.mesada = Mesada.objects.create(
            dependente=self.dependente, grupo_id=r.data["id"],
            valor=100, periodo_recarga="mensal", saldo_atual=100,
        )
        self.conta_dep = Conta.objects.create(usuario=self.dependente, nome="Carteira")

    def test_dependente_cria_meta(self):
        self._como(self.token_dep)
        response = self.client.post("/api/metas/", {"nome": "PS5", "valor_alvo": "3800.00"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_aporte_deduz_da_mesada(self):
        meta = MetaEconomia.objects.create(usuario=self.dependente, nome="PS5", valor_alvo=3800)
        self._como(self.token_dep)
        response = self.client.post(f"/api/metas/{meta.id}/aportar/", {"valor": "30.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mesada.refresh_from_db()
        self.assertEqual(float(self.mesada.saldo_atual), 70.00)
        meta.refresh_from_db()
        self.assertEqual(float(meta.valor_atual), 30.00)

    def test_aporte_acima_da_mesada_bloqueado(self):
        meta = MetaEconomia.objects.create(usuario=self.dependente, nome="PS5", valor_alvo=3800)
        self._como(self.token_dep)
        response = self.client.post(f"/api/metas/{meta.id}/aportar/", {"valor": "150.00"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.mesada.refresh_from_db()
        self.assertEqual(float(self.mesada.saldo_atual), 100.00)


# ══════════════════════════════════════════════════════════════════════════
# Correções da caça a bugs (etapa 19)
# ══════════════════════════════════════════════════════════════════════════

class OrcamentoResumoPeriodoTests(ExtrasTestCase):
    """O realizado do orçamento do grupo deve contar só o mês do período."""

    def setUp(self):
        super().setUp()
        self._como(self.token_joao)
        r = self.client.post("/api/grupos/", {"nome": "Casa"})
        self.grupo_id = r.data["id"]
        Orcamento.objects.create(
            grupo_id=self.grupo_id, categoria=self.cat_alimentacao,
            valor_limite=500, periodo="2026-07-01",
        )
        for data, valor in [("2026-07-10T12:00:00-03:00", 100), ("2026-06-10T12:00:00-03:00", 400)]:
            Transacao.objects.create(
                usuario=self.joao, conta=self.conta_joao, categoria=self.cat_alimentacao,
                tipo="despesa", valor=valor, descricao="Mercado",
                grupo_id=self.grupo_id, data=data,
            )

    def test_realizado_conta_apenas_o_mes_do_orcamento(self):
        self._como(self.token_joao)
        response = self.client.get(f"/api/grupos/{self.grupo_id}/orcamento_resumo/")
        resumo = response.data["orcamentos"][0]
        self.assertEqual(resumo["realizado"], 100.0)
        self.assertEqual(resumo["diferenca"], 400.0)


class PaginacaoTests(ExtrasTestCase):
    def test_page_size_customizavel(self):
        for i in range(25):
            Transacao.objects.create(
                usuario=self.joao, conta=self.conta_joao, categoria=self.cat_alimentacao,
                tipo="despesa", valor=10, descricao=f"Gasto {i}",
            )
        self._como(self.token_joao)
        padrao = self.client.get("/api/transacoes/")
        self.assertEqual(len(padrao.data["results"]), 20)
        maior = self.client.get("/api/transacoes/?page_size=100")
        self.assertEqual(len(maior.data["results"]), 25)


class AdminCriaAdminTests(ExtrasTestCase):
    def test_admin_criado_pela_api_recebe_is_staff(self):
        self._como(self.token_admin)
        response = self.client.post("/api/usuarios/", {
            "email": "novoadmin@test.com", "nome": "Novo Admin",
            "senha": "senha123", "papel_sistema": "admin",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        novo = Usuario.objects.get(email="novoadmin@test.com")
        self.assertTrue(novo.is_staff)


# ══════════════════════════════════════════════════════════════════════════
# Autorização de consultor — endurecimento
# ══════════════════════════════════════════════════════════════════════════

class AutorizacaoSegurancaTests(ExtrasTestCase):
    def test_consultor_nao_se_autoautoriza_em_cliente(self):
        from core.models import AutorizacaoConsultor
        self._como(self.token_maria)
        self.client.post("/api/autorizacoes/", {
            "consultor": self.maria.id, "cliente": self.joao.id, "nivel": "comentar",
        })
        self.assertFalse(
            AutorizacaoConsultor.objects.filter(cliente=self.joao).exists()
        )

    def test_cliente_autoriza_por_email(self):
        self._como(self.token_joao)
        response = self.client.post("/api/autorizacoes/", {
            "consultor_email": "maria@test.com", "nivel": "leitura",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["consultor"], self.maria.id)
        self.assertEqual(response.data["cliente"], self.joao.id)

    def test_email_inexistente_recusado(self):
        self._como(self.token_joao)
        response = self.client.post("/api/autorizacoes/", {
            "consultor_email": "fantasma@test.com", "nivel": "leitura",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nao_autoriza_a_si_mesmo(self):
        self._como(self.token_joao)
        response = self.client.post("/api/autorizacoes/", {
            "consultor": self.joao.id, "nivel": "leitura",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicada_recusada(self):
        self._como(self.token_joao)
        self.client.post("/api/autorizacoes/", {"consultor": self.maria.id, "nivel": "leitura"})
        response = self.client.post("/api/autorizacoes/", {"consultor": self.maria.id, "nivel": "comentar"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ══════════════════════════════════════════════════════════════════════════
# Lembretes por e-mail
# ══════════════════════════════════════════════════════════════════════════

class LembretesEmailTests(ExtrasTestCase):
    def test_conta_vencendo_gera_email(self):
        from django.utils import timezone
        ContaAPagar.objects.create(
            usuario=self.joao, descricao="Aluguel", valor=800,
            vencimento=timezone.localdate(),
        )
        call_command("enviar_lembretes")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Aluguel", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["joao@test.com"])

    def test_orcamento_estourado_gera_email(self):
        from django.utils import timezone
        hoje = timezone.localdate()
        Orcamento.objects.create(
            usuario=self.joao, categoria=self.cat_alimentacao,
            valor_limite=100, periodo=hoje.replace(day=1),
        )
        Transacao.objects.create(
            usuario=self.joao, conta=self.conta_joao, categoria=self.cat_alimentacao,
            tipo="despesa", valor=150, descricao="Mercado",
        )
        call_command("enviar_lembretes")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("estourado", mail.outbox[0].body)

    def test_sem_pendencias_nao_envia(self):
        call_command("enviar_lembretes")
        self.assertEqual(len(mail.outbox), 0)

    def test_conta_paga_nao_gera_email(self):
        from django.utils import timezone
        ContaAPagar.objects.create(
            usuario=self.joao, descricao="Aluguel", valor=800,
            vencimento=timezone.localdate(), pago=True,
        )
        call_command("enviar_lembretes")
        self.assertEqual(len(mail.outbox), 0)
