from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Categoria, Conta, Orcamento, Usuario


class IntegrityTestCase(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user("user@test.com", "Usuario", "senha123")
        login = self.client.post("/api/login/", {"username": "user@test.com", "password": "senha123"})
        self.token = login.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token)
        self.conta = Conta.objects.create(usuario=self.user, nome="Carteira")
        self.cat = Categoria.objects.create(usuario=self.user, nome="Alimentacao", tipo="despesa")

    def test_orcamento_sem_usuario_nem_grupo(self):
        from django.core.exceptions import ValidationError
        o = Orcamento(categoria=self.cat, valor_limite=500, periodo="2026-07-01")
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_orcamento_com_usuario_e_grupo(self):
        from django.core.exceptions import ValidationError
        from core.models import Grupo
        r = self.client.post("/api/grupos/", {"nome": "G"})
        g = Grupo.objects.get(id=r.data["id"])
        o = Orcamento(usuario=self.user, grupo=g, categoria=self.cat, valor_limite=500, periodo="2026-07-01")
        with self.assertRaises(ValidationError):
            o.full_clean()
