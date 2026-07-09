from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Categoria, Conta, Orcamento, Transacao, Usuario
from core.serializers import TransacaoCreateSerializer


class IntegrityTestCase(APITestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user("user@test.com", "Usuario", "senha123")
        self.other = Usuario.objects.create_user("other@test.com", "Other", "senha123")
        login = self.client.post("/api/login/", {"username": "user@test.com", "password": "senha123"})
        self.token = login.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token)
        self.conta = Conta.objects.create(usuario=self.user, nome="Carteira")
        self.cat = Categoria.objects.create(usuario=self.user, nome="Alimentacao", tipo="despesa")
        r = self.client.post("/api/grupos/", {"nome": "Grupo Teste"})
        self.grupo_id = r.data["id"]
        self.client.post(f"/api/grupos/{self.grupo_id}/membros/", {"usuario": self.other.id})

    # ══════════════════════════════════════════════════════════════════════
    # Invariante da soma (teste via serializer direto)
    # ══════════════════════════════════════════════════════════════════════

    def test_divisao_soma_diferente_valor_recusada(self):
        serializer = TransacaoCreateSerializer(data={
            "conta": self.conta.id,
            "categoria": self.cat.id,
            "tipo": "despesa",
            "valor": "100.00",
            "descricao": "Invalido",
            "grupo": self.grupo_id,
            "divisoes": [
                {"participante": self.user.id, "valor_devido": "30.00"},
                {"participante": self.other.id, "valor_devido": "30.00"},
            ],
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("soma", str(serializer.errors).lower())

    def test_divisao_soma_exata_aceita(self):
        serializer = TransacaoCreateSerializer(data={
            "conta": self.conta.id,
            "categoria": self.cat.id,
            "tipo": "despesa",
            "valor": "60.00",
            "descricao": "Valido",
            "grupo": self.grupo_id,
            "divisoes": [
                {"participante": self.user.id, "valor_devido": "30.00"},
                {"participante": self.other.id, "valor_devido": "30.00"},
            ],
        })
        self.assertTrue(serializer.is_valid())

    # ══════════════════════════════════════════════════════════════════════
    # Transação com conta/categoria inválida (teste via model clean)
    # ══════════════════════════════════════════════════════════════════════

    def test_transacao_conta_de_outro_usuario(self):
        from django.core.exceptions import ValidationError

        conta_other = Conta.objects.create(usuario=self.other, nome="Conta do Other")
        t = Transacao(
            usuario=self.user,
            conta=conta_other,
            categoria=self.cat,
            tipo="despesa",
            valor=50,
        )
        with self.assertRaises(ValidationError):
            t.full_clean()

    def test_transacao_categoria_pessoal_de_outro_usuario(self):
        from django.core.exceptions import ValidationError

        cat_other = Categoria.objects.create(usuario=self.other, nome="Cat Other", tipo="despesa")
        t = Transacao(
            usuario=self.user,
            conta=self.conta,
            categoria=cat_other,
            tipo="despesa",
            valor=50,
        )
        with self.assertRaises(ValidationError):
            t.full_clean()

    def test_transacao_com_categoria_padrao_aceita(self):
        cat_padrao = Categoria.objects.create(usuario=None, nome="Padrao", tipo="despesa", padrao=True)
        t = Transacao(
            usuario=self.user,
            conta=self.conta,
            categoria=cat_padrao,
            tipo="despesa",
            valor=50,
        )
        t.full_clean()

    # ══════════════════════════════════════════════════════════════════════
    # Orçamento — validações de modelo
    # ══════════════════════════════════════════════════════════════════════

    def test_orcamento_sem_usuario_nem_grupo(self):
        from django.core.exceptions import ValidationError

        o = Orcamento(categoria=self.cat, valor_limite=500, periodo="2026-07-01")
        with self.assertRaises(ValidationError):
            o.full_clean()

    def test_orcamento_com_usuario_e_grupo(self):
        from django.core.exceptions import ValidationError
        from core.models import Grupo

        g = Grupo.objects.get(id=self.grupo_id)
        o = Orcamento(usuario=self.user, grupo=g, categoria=self.cat, valor_limite=500, periodo="2026-07-01")
        with self.assertRaises(ValidationError):
            o.full_clean()

    # ══════════════════════════════════════════════════════════════════════
    # DivisaoDespesa — validações de modelo
    # ══════════════════════════════════════════════════════════════════════

    def test_divisao_valor_zero_ou_negativo(self):
        from django.core.exceptions import ValidationError
        from core.models import DivisaoDespesa

        t = Transacao.objects.create(
            usuario=self.user, conta=self.conta, categoria=self.cat,
            tipo="despesa", valor=100, grupo_id=self.grupo_id,
        )
        d = DivisaoDespesa(transacao=t, participante=self.other, valor_devido=0)
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_divisao_em_receita_recusada(self):
        from django.core.exceptions import ValidationError
        from core.models import DivisaoDespesa

        t = Transacao.objects.create(
            usuario=self.user, conta=self.conta, categoria=self.cat,
            tipo="receita", valor=100, grupo_id=self.grupo_id,
        )
        d = DivisaoDespesa(transacao=t, participante=self.other, valor_devido=50)
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_divisao_sem_grupo_recusada(self):
        from django.core.exceptions import ValidationError
        from core.models import DivisaoDespesa

        t = Transacao.objects.create(
            usuario=self.user, conta=self.conta, categoria=self.cat,
            tipo="despesa", valor=50,
        )
        d = DivisaoDespesa(transacao=t, participante=self.other, valor_devido=25)
        with self.assertRaises(ValidationError):
            d.full_clean()
