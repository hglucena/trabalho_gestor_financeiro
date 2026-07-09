from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Conta, Categoria, Transacao, Usuario, AutorizacaoConsultor, Recomendacao


class ConsultorTestCase(APITestCase):
    def setUp(self):
        self.cliente = Usuario.objects.create_user("cliente@test.com", "Cliente", "senha123")
        self.consultor_leitura = Usuario.objects.create_user("consultor-l@test.com", "Consultor L", "senha123")
        self.consultor_comentar = Usuario.objects.create_user("consultor-c@test.com", "Consultor C", "senha123")
        self.estranho = Usuario.objects.create_user("estranho@test.com", "Estranho", "senha123")

        login = self.client.post("/api/login/", {"username": "cliente@test.com", "password": "senha123"})
        self.token_cliente = login.data["token"]
        login = self.client.post("/api/login/", {"username": "consultor-l@test.com", "password": "senha123"})
        self.token_leitura = login.data["token"]
        login = self.client.post("/api/login/", {"username": "consultor-c@test.com", "password": "senha123"})
        self.token_comentar = login.data["token"]
        login = self.client.post("/api/login/", {"username": "estranho@test.com", "password": "senha123"})
        self.token_estranho = login.data["token"]

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_cliente)
        self.conta = Conta.objects.create(usuario=self.cliente, nome="Carteira Cliente")
        self.cat = Categoria.objects.create(usuario=self.cliente, nome="Alimentacao", tipo="despesa")
        Transacao.objects.create(
            usuario=self.cliente, conta=self.conta, categoria=self.cat,
            tipo="despesa", valor=100, descricao="Mercado",
        )

    # ── Autorização ────────────────────────────────────────────────────

    def test_cliente_autoriza_consultor(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_cliente)
        response = self.client.post("/api/autorizacoes/", {
            "consultor": self.consultor_leitura.id, "cliente": self.cliente.id, "nivel": "leitura",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_cliente_revoga_autorizacao(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_cliente)
        r = self.client.post("/api/autorizacoes/", {
            "consultor": self.consultor_leitura.id, "cliente": self.cliente.id, "nivel": "leitura",
        })
        aid = r.data["id"]
        response = self.client.delete(f"/api/autorizacoes/{aid}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_autorizacao_duplicada_recusada(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_cliente)
        self.client.post("/api/autorizacoes/", {
            "consultor": self.consultor_leitura.id, "cliente": self.cliente.id, "nivel": "leitura",
        })
        response = self.client.post("/api/autorizacoes/", {
            "consultor": self.consultor_leitura.id, "cliente": self.cliente.id, "nivel": "comentar",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Acesso — consultor autorizado vê dados do cliente ──────────────

    def test_consultor_autorizado_ve_clientes(self):
        AutorizacaoConsultor.objects.create(
            consultor=self.consultor_leitura, cliente=self.cliente, nivel="leitura", status=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.get("/api/consultor/clientes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [c["id"] for c in (response.data.get("results") or response.data)]
        self.assertIn(self.cliente.id, ids)

    def test_consultor_autorizado_ve_transacoes(self):
        AutorizacaoConsultor.objects.create(
            consultor=self.consultor_leitura, cliente=self.cliente, nivel="leitura", status=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.get(f"/api/consultor/clientes/{self.cliente.id}/transacoes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data.get("results") or response.data), 0)

    def test_consultor_autorizado_ve_contas(self):
        AutorizacaoConsultor.objects.create(
            consultor=self.consultor_leitura, cliente=self.cliente, nivel="leitura", status=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.get(f"/api/consultor/clientes/{self.cliente.id}/contas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data.get("results") or response.data), 0)

    # ── Acesso — sem autorização → negado ─────────────────────────────

    def test_consultor_nao_autorizado_nao_ve_cliente(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.get("/api/consultor/clientes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count", 0), 0)

    def test_consultor_nao_autorizado_nao_acessa_transacoes(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.get(f"/api/consultor/clientes/{self.cliente.id}/transacoes/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_autorizacao_inativa_nao_permite_acesso(self):
        autoriz = AutorizacaoConsultor.objects.create(
            consultor=self.consultor_leitura, cliente=self.cliente, nivel="leitura", status=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.get(f"/api/consultor/clientes/{self.cliente.id}/transacoes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        autoriz.status = False
        autoriz.save()
        response = self.client.get(f"/api/consultor/clientes/{self.cliente.id}/transacoes/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ── Recomendação — nível leitura não pode comentar ────────────────

    def test_consultor_leitura_nao_cria_recomendacao(self):
        AutorizacaoConsultor.objects.create(
            consultor=self.consultor_leitura, cliente=self.cliente, nivel="leitura", status=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.post("/api/recomendacoes/", {
            "cliente": self.cliente.id, "texto": "Recomendação de teste",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_consultor_comentar_cria_recomendacao(self):
        AutorizacaoConsultor.objects.create(
            consultor=self.consultor_comentar, cliente=self.cliente, nivel="comentar", status=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_comentar)
        response = self.client.post("/api/recomendacoes/", {
            "cliente": self.cliente.id, "texto": "Sugestão de economia",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nome_cliente"], "Cliente")

    def test_consultor_sem_autorizacao_nao_cria_recomendacao(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.post("/api/recomendacoes/", {
            "cliente": self.cliente.id, "texto": "Não deveria funcionar",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cliente_ve_recomendacoes_recebidas(self):
        AutorizacaoConsultor.objects.create(
            consultor=self.consultor_comentar, cliente=self.cliente, nivel="comentar", status=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_comentar)
        self.client.post("/api/recomendacoes/", {
            "cliente": self.cliente.id, "texto": "Recomendação 1",
        })
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_cliente)
        response = self.client.get("/api/recomendacoes/")
        self.assertGreaterEqual(response.data.get("count", 0), 1)

    # ── Modo leitura — consultor não altera dados ─────────────────────

    def test_consultor_nao_edita_transacao_do_cliente(self):
        AutorizacaoConsultor.objects.create(
            consultor=self.consultor_comentar, cliente=self.cliente, nivel="comentar", status=True,
        )
        tx = Transacao.objects.filter(usuario=self.cliente).first()
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_comentar)
        response = self.client.patch(f"/api/transacoes/{tx.id}/", {"descricao": "Alterado"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_consultor_nao_ve_grupos_do_cliente(self):
        AutorizacaoConsultor.objects.create(
            consultor=self.consultor_leitura, cliente=self.cliente, nivel="leitura", status=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_leitura)
        response = self.client.get("/api/grupos/")
        self.assertEqual(response.data["count"], 0)
