from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Conta, Categoria, Grupo, MembroGrupo, Mesada, Transacao, Usuario


class DependenteTestCase(APITestCase):
    def setUp(self):
        self.gestor = Usuario.objects.create_user("gestor@test.com", "Gestor", "senha123")
        self.dependente = Usuario.objects.create_user("dep@test.com", "Dependente", "senha123")
        self.membro = Usuario.objects.create_user("membro@test.com", "Membro", "senha123")
        self.estranho = Usuario.objects.create_user("estranho@test.com", "Estranho", "senha123")

        login = self.client.post("/api/login/", {"username": "gestor@test.com", "password": "senha123"})
        self.token_gestor = login.data["token"]
        login = self.client.post("/api/login/", {"username": "dep@test.com", "password": "senha123"})
        self.token_dep = login.data["token"]
        login = self.client.post("/api/login/", {"username": "membro@test.com", "password": "senha123"})
        self.token_membro = login.data["token"]
        login = self.client.post("/api/login/", {"username": "estranho@test.com", "password": "senha123"})
        self.token_estranho = login.data["token"]

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        r = self.client.post("/api/grupos/", {"nome": "Familia"})
        self.grupo_id = r.data["id"]
        self.client.post(f"/api/grupos/{self.grupo_id}/membros/", {"usuario": self.dependente.id, "papel_no_grupo": "dependente"})
        self.client.post(f"/api/grupos/{self.grupo_id}/membros/", {"usuario": self.membro.id})

        self.categoria = Categoria.objects.create(usuario=None, nome="Alimentacao", tipo="despesa", padrao=True)
        self.cat_dep = Categoria.objects.create(usuario=self.dependente, nome="Pessoal", tipo="despesa")

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        self.conta_dep = Conta.objects.create(usuario=self.dependente, nome="Carteira Dep")

    # ══════════════════════════════════════════════════════════════════════
    # Mesada — acesso e CRUD
    # ══════════════════════════════════════════════════════════════════════

    def test_gestor_cria_mesada_para_dependente(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        response = self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id,
            "grupo": self.grupo_id,
            "valor": "200.00",
            "periodo_recarga": "semanal",
            "saldo_atual": "200.00",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["nome_dependente"], "Dependente")
        self.assertEqual(float(response.data["saldo_atual"]), 200.00)

    def test_membro_nao_cria_mesada(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_membro)
        response = self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id,
            "grupo": self.grupo_id,
            "valor": "100.00",
            "periodo_recarga": "semanal",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dependente_ve_propria_mesada(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id,
            "grupo": self.grupo_id,
            "valor": "200.00",
            "periodo_recarga": "semanal",
            "saldo_atual": "200.00",
        })
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.get("/api/mesadas/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_dependente_nao_ve_mesada_de_outro(self):
        outro = Usuario.objects.create_user("dep2@test.com", "Dep2", "senha123")
        MembroGrupo.objects.create(grupo_id=self.grupo_id, usuario=outro, papel_no_grupo="dependente")
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id, "grupo": self.grupo_id,
            "valor": "100.00", "periodo_recarga": "semanal", "saldo_atual": "100.00",
        })
        self.client.post("/api/mesadas/", {
            "dependente": outro.id, "grupo": self.grupo_id,
            "valor": "50.00", "periodo_recarga": "semanal", "saldo_atual": "50.00",
        })
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.get("/api/mesadas/")
        self.assertEqual(response.data["count"], 1)

    def test_dependente_nao_pode_alterar_mesada(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        r = self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id, "grupo": self.grupo_id,
            "valor": "200.00", "periodo_recarga": "mensal", "saldo_atual": "200.00",
        })
        mid = r.data["id"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.patch(f"/api/mesadas/{mid}/", {"saldo_atual": "500.00"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_estranho_nao_ve_mesada(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id, "grupo": self.grupo_id,
            "valor": "200.00", "periodo_recarga": "semanal", "saldo_atual": "200.00",
        })
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_estranho)
        response = self.client.get("/api/mesadas/")
        self.assertEqual(response.data["count"], 0)

    # ══════════════════════════════════════════════════════════════════════
    # Dependente — isolamento de grupo
    # ══════════════════════════════════════════════════════════════════════

    def test_dependente_nao_ve_grupos(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.get("/api/grupos/")
        self.assertEqual(response.data["count"], 0)

    def test_dependente_nao_ve_transacoes_do_grupo(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        conta_g = Conta.objects.create(usuario=self.gestor, nome="Carteira Gestor")
        Transacao.objects.create(
            usuario=self.gestor, conta=conta_g, categoria=self.categoria,
            tipo="despesa", valor=100, descricao="Grupo", grupo_id=self.grupo_id,
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.get("/api/transacoes/")
        ids = [t["id"] for t in response.data["results"]]
        self.assertEqual(len(ids), 0)

    def test_dependente_ve_proprias_transacoes(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        Transacao.objects.create(
            usuario=self.dependente, conta=self.conta_dep, categoria=self.cat_dep,
            tipo="despesa", valor=30, descricao="Pessoal",
        )
        response = self.client.get("/api/transacoes/")
        self.assertEqual(response.data["count"], 1)

    def test_dependente_nao_ve_orcamentos_do_grupo(self):
        from core.models import Orcamento
        Orcamento.objects.create(
            grupo_id=self.grupo_id, categoria=self.categoria,
            valor_limite=500, periodo="2026-07-01",
        )
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.get("/api/orcamentos/")
        self.assertEqual(response.data["count"], 0)

    def test_dependente_nao_acessa_membros_do_grupo(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.get(f"/api/grupos/{self.grupo_id}/membros/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dependente_nao_acessa_quem_deve_a_quem(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.get(f"/api/grupos/{self.grupo_id}/quem_deve_a_quem/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ══════════════════════════════════════════════════════════════════════
    # Regra de negócio — limite da mesada
    # ══════════════════════════════════════════════════════════════════════

    def test_gasto_dentro_do_limite_aceito(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id, "grupo": self.grupo_id,
            "valor": "200.00", "periodo_recarga": "semanal", "saldo_atual": "200.00",
        })
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.post("/api/transacoes/", {
            "conta": self.conta_dep.id, "categoria": self.cat_dep.id,
            "tipo": "despesa", "valor": "50.00", "descricao": "Lanche",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_gasto_acima_do_limite_bloqueado(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id, "grupo": self.grupo_id,
            "valor": "100.00", "periodo_recarga": "semanal", "saldo_atual": "50.00",
        })
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        response = self.client.post("/api/transacoes/", {
            "conta": self.conta_dep.id, "categoria": self.cat_dep.id,
            "tipo": "despesa", "valor": "80.00", "descricao": "Compra grande",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_gastos_acumulados_deduzem_saldo(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        r = self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id, "grupo": self.grupo_id,
            "valor": "200.00", "periodo_recarga": "semanal", "saldo_atual": "200.00",
        })
        mid = r.data["id"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        self.client.post("/api/transacoes/", {
            "conta": self.conta_dep.id, "categoria": self.cat_dep.id,
            "tipo": "despesa", "valor": "60.00", "descricao": "Gasto 1",
        })
        self.client.post("/api/transacoes/", {
            "conta": self.conta_dep.id, "categoria": self.cat_dep.id,
            "tipo": "despesa", "valor": "40.00", "descricao": "Gasto 2",
        })
        mesada = Mesada.objects.get(id=mid)
        self.assertEqual(float(mesada.saldo_atual), 100.00)

    def test_gasto_apos_esgotar_saldo_bloqueado(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id, "grupo": self.grupo_id,
            "valor": "200.00", "periodo_recarga": "mensal", "saldo_atual": "30.00",
        })
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        self.client.post("/api/transacoes/", {
            "conta": self.conta_dep.id, "categoria": self.cat_dep.id,
            "tipo": "despesa", "valor": "30.00", "descricao": "Gasto 1",
        })
        response = self.client.post("/api/transacoes/", {
            "conta": self.conta_dep.id, "categoria": self.cat_dep.id,
            "tipo": "despesa", "valor": "0.01", "descricao": "Gasto 2",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_receita_nao_afeta_mesada(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_gestor)
        r = self.client.post("/api/mesadas/", {
            "dependente": self.dependente.id, "grupo": self.grupo_id,
            "valor": "200.00", "periodo_recarga": "semanal", "saldo_atual": "200.00",
        })
        mid = r.data["id"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token_dep)
        self.client.post("/api/transacoes/", {
            "conta": self.conta_dep.id, "categoria": self.cat_dep.id,
            "tipo": "receita", "valor": "100.00", "descricao": "Presente",
        })
        mesada = Mesada.objects.get(id=mid)
        self.assertEqual(float(mesada.saldo_atual), 200.00)
