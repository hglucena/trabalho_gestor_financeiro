from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Categoria, Conta, Grupo, MembroGrupo, Orcamento, Transacao, Usuario


class CrudTestCase(APITestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser("admin@test.com", "Admin", "senha123")
        self.user = Usuario.objects.create_user("user@test.com", "Usuario", "senha123")
        self.other = Usuario.objects.create_user("other@test.com", "Other", "senha123")

        login = self.client.post("/api/login/", {"username": "user@test.com", "password": "senha123"})
        self.token = login.data["token"]
        login = self.client.post("/api/login/", {"username": "admin@test.com", "password": "senha123"})
        self.token_admin = login.data["token"]
        login = self.client.post("/api/login/", {"username": "other@test.com", "password": "senha123"})
        self.token_other = login.data["token"]

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token)

    # ══════════════════════════════════════════════════════════════════════
    # Conta
    # ══════════════════════════════════════════════════════════════════════

    def test_criar_conta(self):
        response = self.client.post("/api/contas/", {"nome": "Carteira", "saldo_inicial": "100.00"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nome"], "Carteira")
        self.assertEqual(response.data["usuario"], self.user.id)

    def test_listar_contas(self):
        Conta.objects.create(usuario=self.user, nome="C1")
        Conta.objects.create(usuario=self.user, nome="C2")
        response = self.client.get("/api/contas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_detalhe_conta(self):
        conta = Conta.objects.create(usuario=self.user, nome="Minha")
        response = self.client.get(f"/api/contas/{conta.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nome"], "Minha")

    def test_atualizar_conta(self):
        conta = Conta.objects.create(usuario=self.user, nome="Velha")
        response = self.client.patch(f"/api/contas/{conta.id}/", {"nome": "Nova"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nome"], "Nova")

    def test_deletar_conta(self):
        conta = Conta.objects.create(usuario=self.user, nome="Deletar")
        response = self.client.delete(f"/api/contas/{conta.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ══════════════════════════════════════════════════════════════════════
    # Categoria
    # ══════════════════════════════════════════════════════════════════════

    def test_criar_categoria(self):
        response = self.client.post("/api/categorias/", {"nome": "Alimentacao", "tipo": "despesa"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nome"], "Alimentacao")
        self.assertEqual(response.data["usuario"], self.user.id)

    def test_listar_categorias(self):
        Categoria.objects.create(usuario=self.user, nome="C1", tipo="despesa")
        Categoria.objects.create(usuario=None, nome="Padrao", tipo="despesa", padrao=True)
        response = self.client.get("/api/categorias/")
        self.assertEqual(response.data["count"], 2)

    def test_editar_categoria_propria(self):
        cat = Categoria.objects.create(usuario=self.user, nome="Original", tipo="despesa")
        response = self.client.patch(f"/api/categorias/{cat.id}/", {"nome": "Editada"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_nao_editar_categoria_padrao(self):
        cat = Categoria.objects.create(usuario=None, nome="Sistema", tipo="despesa", padrao=True)
        response = self.client.patch(f"/api/categorias/{cat.id}/", {"nome": "Hack"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cria_categoria_padrao(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_admin)
        response = self.client.post("/api/categorias/", {"nome": "Transporte", "tipo": "despesa"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cat = Categoria.objects.get(id=response.data["id"])
        self.assertIsNone(cat.usuario)
        self.assertTrue(cat.padrao)

    def test_admin_so_ve_categorias_padrao(self):
        Categoria.objects.create(usuario=None, nome="Sistema", tipo="despesa", padrao=True)
        Categoria.objects.create(usuario=self.user, nome="Pessoal", tipo="despesa")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_admin)
        response = self.client.get("/api/categorias/")
        self.assertEqual(response.data["count"], 1)

    # ══════════════════════════════════════════════════════════════════════
    # Transação
    # ══════════════════════════════════════════════════════════════════════

    def test_criar_transacao(self):
        conta = Conta.objects.create(usuario=self.user, nome="Carteira")
        cat = Categoria.objects.create(usuario=self.user, nome="Alimentacao", tipo="despesa")
        response = self.client.post("/api/transacoes/", {
            "conta": conta.id, "categoria": cat.id, "tipo": "despesa",
            "valor": "50.00", "descricao": "Mercado",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["valor"], "50.00")

    def test_listar_transacoes(self):
        conta = Conta.objects.create(usuario=self.user, nome="Carteira")
        cat = Categoria.objects.create(usuario=self.user, nome="Alimentacao", tipo="despesa")
        Transacao.objects.create(usuario=self.user, conta=conta, categoria=cat, tipo="despesa", valor=50)
        Transacao.objects.create(usuario=self.user, conta=conta, categoria=cat, tipo="receita", valor=100)
        response = self.client.get("/api/transacoes/")
        self.assertEqual(response.data["count"], 2)

    def test_detalhe_transacao(self):
        conta = Conta.objects.create(usuario=self.user, nome="Carteira")
        cat = Categoria.objects.create(usuario=self.user, nome="Alimentacao", tipo="despesa")
        t = Transacao.objects.create(usuario=self.user, conta=conta, categoria=cat, tipo="despesa", valor=50)
        response = self.client.get(f"/api/transacoes/{t.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["usuario"], self.user.id)

    def test_atualizar_transacao(self):
        conta = Conta.objects.create(usuario=self.user, nome="Carteira")
        cat = Categoria.objects.create(usuario=self.user, nome="Alimentacao", tipo="despesa")
        t = Transacao.objects.create(usuario=self.user, conta=conta, categoria=cat, tipo="despesa", valor=50)
        response = self.client.patch(f"/api/transacoes/{t.id}/", {"descricao": "Update"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["descricao"], "Update")

    def test_deletar_transacao(self):
        conta = Conta.objects.create(usuario=self.user, nome="Carteira")
        cat = Categoria.objects.create(usuario=self.user, nome="Alimentacao", tipo="despesa")
        t = Transacao.objects.create(usuario=self.user, conta=conta, categoria=cat, tipo="despesa", valor=50)
        response = self.client.delete(f"/api/transacoes/{t.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ══════════════════════════════════════════════════════════════════════
    # Grupo
    # ══════════════════════════════════════════════════════════════════════

    def test_criar_grupo(self):
        response = self.client.post("/api/grupos/", {"nome": "Republica"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["responsavel"], self.user.id)
        membro = MembroGrupo.objects.get(grupo_id=response.data["id"], usuario=self.user)
        self.assertEqual(membro.papel_no_grupo, "responsavel")

    def test_listar_grupos(self):
        self.client.post("/api/grupos/", {"nome": "G1"})
        self.client.post("/api/grupos/", {"nome": "G2"})
        response = self.client.get("/api/grupos/")
        self.assertEqual(response.data["count"], 2)

    def test_detalhe_grupo(self):
        r = self.client.post("/api/grupos/", {"nome": "G"})
        gid = r.data["id"]
        response = self.client.get(f"/api/grupos/{gid}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_gestor_edita_grupo(self):
        r = self.client.post("/api/grupos/", {"nome": "Original"})
        gid = r.data["id"]
        response = self.client.patch(f"/api/grupos/{gid}/", {"nome": "Editado"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nome"], "Editado")

    # ══════════════════════════════════════════════════════════════════════
    # MembroGrupo
    # ══════════════════════════════════════════════════════════════════════

    def test_adicionar_membro(self):
        r = self.client.post("/api/grupos/", {"nome": "G"})
        gid = r.data["id"]
        response = self.client.post(f"/api/grupos/{gid}/membros/", {"usuario": self.other.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_listar_membros(self):
        r = self.client.post("/api/grupos/", {"nome": "G"})
        gid = r.data["id"]
        self.client.post(f"/api/grupos/{gid}/membros/", {"usuario": self.other.id})
        response = self.client.get(f"/api/grupos/{gid}/membros/")
        self.assertEqual(response.data["count"], 2)

    def test_remover_membro(self):
        r = self.client.post("/api/grupos/", {"nome": "G"})
        gid = r.data["id"]
        mr = self.client.post(f"/api/grupos/{gid}/membros/", {"usuario": self.other.id})
        mid = mr.data["id"]
        response = self.client.delete(f"/api/grupos/{gid}/membros/{mid}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    # ══════════════════════════════════════════════════════════════════════
    # Orçamento
    # ══════════════════════════════════════════════════════════════════════

    def test_criar_orcamento_pessoal(self):
        cat = Categoria.objects.create(usuario=self.user, nome="Lazer", tipo="despesa")
        response = self.client.post("/api/orcamentos/", {
            "categoria": cat.id, "valor_limite": "500.00", "periodo": "2026-07-01",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["usuario"], self.user.id)

    def test_listar_orcamentos(self):
        cat = Categoria.objects.create(usuario=self.user, nome="Lazer", tipo="despesa")
        Orcamento.objects.create(usuario=self.user, categoria=cat, valor_limite=500, periodo="2026-07-01")
        response = self.client.get("/api/orcamentos/")
        self.assertEqual(response.data["count"], 1)

    def test_atualizar_orcamento(self):
        cat = Categoria.objects.create(usuario=self.user, nome="Lazer", tipo="despesa")
        o = Orcamento.objects.create(usuario=self.user, categoria=cat, valor_limite=500, periodo="2026-07-01")
        response = self.client.patch(f"/api/orcamentos/{o.id}/", {"valor_limite": "300.00"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
