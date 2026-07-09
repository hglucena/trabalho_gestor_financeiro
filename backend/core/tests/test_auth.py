from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Usuario


class AuthTestCase(APITestCase):
    def test_registro_usuario_comum(self):
        response = self.client.post("/api/registro/", {
            "email": "novo@teste.com",
            "nome": "Novo Usuario",
            "senha": "senha123",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "novo@teste.com")
        self.assertNotIn("papel_sistema", response.data)
        self.assertNotIn("senha", response.data)

    def test_registro_email_duplicado(self):
        Usuario.objects.create_user("dup@teste.com", "Duplicado", "senha123")
        response = self.client.post("/api/registro/", {
            "email": "dup@teste.com",
            "nome": "Outro",
            "senha": "senha123",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_credenciais_corretas(self):
        Usuario.objects.create_user("login@teste.com", "Login", "senha123")
        response = self.client.post("/api/login/", {
            "username": "login@teste.com",
            "password": "senha123",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["usuario"]["email"], "login@teste.com")
        self.assertEqual(response.data["usuario"]["papel_sistema"], "comum")

    def test_login_senha_errada(self):
        Usuario.objects.create_user("login2@teste.com", "Login", "senha123")
        response = self.client.post("/api/login/", {
            "username": "login2@teste.com",
            "password": "errada",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_com_token(self):
        Usuario.objects.create_user("eu@teste.com", "Eu Mesmo", "senha123")
        login = self.client.post("/api/login/", {
            "username": "eu@teste.com", "password": "senha123",
        })
        token = login.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)
        response = self.client.get("/api/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "eu@teste.com")
        self.assertEqual(response.data["papel_sistema"], "comum")

    def test_me_sem_token(self):
        response = self.client.get("/api/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_registro_cria_papel_comum(self):
        response = self.client.post("/api/registro/", {
            "email": "comum@teste.com",
            "nome": "Comum",
            "senha": "senha123",
        })
        usuario = Usuario.objects.get(email="comum@teste.com")
        self.assertEqual(usuario.papel_sistema, "comum")

    def test_superuser_papel_admin(self):
        admin = Usuario.objects.create_superuser("super@teste.com", "Super", "senha123")
        self.assertEqual(admin.papel_sistema, "admin")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
