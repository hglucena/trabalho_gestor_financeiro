from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Conta, Categoria, Grupo, MembroGrupo, Orcamento, Transacao, Usuario


class BusinessTestCase(APITestCase):
    def setUp(self):
        self.gestor = Usuario.objects.create_user("gestor@test.com", "Gestor", "senha123")
        self.membro_a = Usuario.objects.create_user("ma@test.com", "Membro A", "senha123")
        self.membro_b = Usuario.objects.create_user("mb@test.com", "Membro B", "senha123")
        login = self.client.post("/api/login/", {"username": "gestor@test.com", "password": "senha123"})
        self.token_gestor = login.data["token"]
        login = self.client.post("/api/login/", {"username": "ma@test.com", "password": "senha123"})
        self.token_a = login.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        self.conta = Conta.objects.create(usuario=self.gestor, nome="Carteira")
        self.cat = Categoria.objects.create(usuario=self.gestor, nome="Alimentacao", tipo="despesa")
        r = self.client.post("/api/grupos/", {"nome": "Republica"})
        self.grupo_id = r.data["id"]
        self.client.post(f"/api/grupos/{self.grupo_id}/membros/", {"usuario": self.membro_a.id})
        self.client.post(f"/api/grupos/{self.grupo_id}/membros/", {"usuario": self.membro_b.id})

    def test_criador_vira_responsavel(self):
        mg = MembroGrupo.objects.get(grupo_id=self.grupo_id, usuario=self.gestor)
        self.assertEqual(mg.papel_no_grupo, "responsavel")

    def test_membro_entra_como_membro(self):
        mg = MembroGrupo.objects.get(grupo_id=self.grupo_id, usuario=self.membro_a)
        self.assertEqual(mg.papel_no_grupo, "membro")

    def test_quem_deve_a_quem_endpoint_funciona(self):
        response = self.client.get(f"/api/grupos/{self.grupo_id}/quem_deve_a_quem/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["grupo"], "Republica")
        self.assertEqual(len(response.data["membros"]), 3)

    def test_orcamento_resumo_endpoint(self):
        Orcamento.objects.create(grupo_id=self.grupo_id, categoria=self.cat, valor_limite=200, periodo="2026-07-01")
        response = self.client.get(f"/api/grupos/{self.grupo_id}/orcamento_resumo/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["orcamentos"]), 1)

    def test_membro_nao_cria_orcamento_grupo(self):
        cat = Categoria.objects.create(usuario=self.membro_a, nome="Lazer", tipo="despesa")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_a)
        response = self.client.post("/api/orcamentos/", {
            "grupo": self.grupo_id, "categoria": cat.id,
            "valor_limite": "100.00", "periodo": "2026-07-01",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_fluxo_completo_mvp(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        r = self.client.post("/api/contas/", {"nome": "Carteira Fluxo", "saldo_inicial": "500.00"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        cid = r.data["id"]
        r = self.client.post("/api/categorias/", {"nome": "Mercado Fluxo", "tipo": "despesa"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        cat_id = r.data["id"]
        r = self.client.post("/api/transacoes/", {
            "conta": cid, "categoria": cat_id, "tipo": "despesa",
            "valor": "150.00", "descricao": "Compras do mes",
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        r = self.client.post("/api/grupos/", {"nome": "Minha Republica"})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        gid = r.data["id"]
        r = self.client.post(f"/api/grupos/{gid}/membros/", {"usuario": self.membro_a.id})
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        r = self.client.get(f"/api/grupos/{gid}/quem_deve_a_quem/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.get(f"/api/grupos/{gid}/saldo/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r = self.client.get("/api/transacoes/")
        self.assertEqual(r.status_code, status.HTTP_200_OK)
