from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Conta, Categoria, Grupo, MembroGrupo, Transacao, Usuario


class PermissionsTestCase(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser("admin@test.com", "Admin", "senha123")
        self.gestor = Usuario.objects.create_user("gestor@test.com", "Gestor", "senha123")
        self.membro = Usuario.objects.create_user("membro@test.com", "Membro", "senha123")
        self.outro = Usuario.objects.create_user("outro@test.com", "Outro", "senha123")

        login = self.client.post("/api/login/", {"username": "gestor@test.com", "password": "senha123"})
        self.token_gestor = login.data["token"]
        login = self.client.post("/api/login/", {"username": "membro@test.com", "password": "senha123"})
        self.token_membro = login.data["token"]
        login = self.client.post("/api/login/", {"username": "outro@test.com", "password": "senha123"})
        self.token_outro = login.data["token"]
        login = self.client.post("/api/login/", {"username": "admin@test.com", "password": "senha123"})
        self.token_admin = login.data["token"]

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        self.conta_gestor = Conta.objects.create(usuario=self.gestor, nome="Carteira Gestor")
        self.cat_gestor = Categoria.objects.create(usuario=self.gestor, nome="Alimentacao", tipo="despesa")
        self.client.post("/api/grupos/", {"nome": "Grupo Teste", "descricao": "G"}
                        ).data.get("id")
        self.grupo = Grupo.objects.first()
        MembroGrupo.objects.create(grupo=self.grupo, usuario=self.membro, papel_no_grupo="membro")

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        self.conta_membro = Conta.objects.create(usuario=self.membro, nome="Carteira Membro")
        cat_membro = Categoria.objects.create(usuario=self.membro, nome="Pessoal", tipo="despesa")
        Transacao.objects.create(
            usuario=self.membro, conta=self.conta_membro, categoria=cat_membro,
            tipo="despesa", valor=50, descricao="Pessoal do Membro"
        )

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        Transacao.objects.create(
            usuario=self.gestor, conta=self.conta_gestor, categoria=self.cat_gestor,
            tipo="despesa", valor=100, descricao="Grupo", grupo=self.grupo,
        )

    # ══════════════════════════════════════════════════════════════════════
    # Conta — isolamento
    # ══════════════════════════════════════════════════════════════════════

    def test_outro_nao_ve_contas_do_gestor(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_outro)
        response = self.client.get("/api/contas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_outro_nao_acessa_detalhe_conta_gestor(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_outro)
        response = self.client.get(f"/api/contas/{self.conta_gestor.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_membro_nao_edita_conta_gestor(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        response = self.client.patch(f"/api/contas/{self.conta_gestor.id}/", {"nome": "Hack"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ══════════════════════════════════════════════════════════════════════
    # Transação — isolamento
    # ══════════════════════════════════════════════════════════════════════

    def test_membro_nao_ve_transacao_pessoal_gestor(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        t_pessoal = Transacao.objects.create(
            usuario=self.gestor, conta=self.conta_gestor,
            categoria=self.cat_gestor, tipo="despesa", valor=30, descricao="Pessoal do Gestor",
        )
        response = self.client.get("/api/transacoes/")
        ids = [t["id"] for t in response.data["results"]]
        self.assertNotIn(t_pessoal.id, ids)

    def test_membro_ve_transacao_do_grupo(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        response = self.client.get("/api/transacoes/")
        ids = [t["id"] for t in response.data["results"]]
        t_grupo = Transacao.objects.filter(grupo=self.grupo).first()
        self.assertIn(t_grupo.id, ids)

    def test_outro_nao_edita_transacao_gestor(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_outro)
        t = Transacao.objects.filter(grupo__isnull=True, usuario=self.gestor).first()
        if not t:
            t = Transacao.objects.create(
                usuario=self.gestor, conta=self.conta_gestor,
                categoria=self.cat_gestor, tipo="despesa", valor=30,
            )
        response = self.client.patch(f"/api/transacoes/{t.id}/", {"descricao": "Hack"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ══════════════════════════════════════════════════════════════════════
    # Admin — bloqueado de finanças
    # ══════════════════════════════════════════════════════════════════════

    def test_admin_nao_ve_transacoes(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_admin)
        response = self.client.get("/api/transacoes/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_nao_ve_contas(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_admin)
        response = self.client.get("/api/contas/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_nao_cria_conta(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_admin)
        response = self.client.post("/api/contas/", {"nome": "Hack", "saldo_inicial": "999"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ══════════════════════════════════════════════════════════════════════
    # Grupo — gestor vs membro
    # ══════════════════════════════════════════════════════════════════════

    def test_membro_nao_edita_grupo(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        response = self.client.patch(f"/api/grupos/{self.grupo.id}/", {"nome": "Hack"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_membro_nao_deleta_grupo(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        response = self.client.delete(f"/api/grupos/{self.grupo.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_membro_nao_adiciona_membro(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        response = self.client.post(
            f"/api/grupos/{self.grupo.id}/membros/",
            {"usuario": self.outro.id},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_nao_membro_nao_ve_grupo(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_outro)
        response = self.client.get(f"/api/grupos/{self.grupo.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_membro_ve_grupo(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        response = self.client.get(f"/api/grupos/{self.grupo.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ══════════════════════════════════════════════════════════════════════
    # Sem token
    # ══════════════════════════════════════════════════════════════════════

    def test_sem_token_negado(self):
        self.client.credentials()
        endpoints = ["/api/contas/", "/api/transacoes/", "/api/grupos/", "/api/usuarios/"]
        for ep in endpoints:
            with self.subTest(endpoint=ep):
                response = self.client.get(ep)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ══════════════════════════════════════════════════════════════════════
    # Admin — usuários
    # ══════════════════════════════════════════════════════════════════════

    def test_admin_ve_usuarios(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_admin)
        response = self.client.get("/api/usuarios/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_comum_nao_ve_usuarios(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        response = self.client.get("/api/usuarios/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
