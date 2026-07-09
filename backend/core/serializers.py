from rest_framework import serializers
from core.models import Usuario


class CadastroSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = Usuario
        fields = ["id", "email", "nome", "senha"]

    def create(self, validated_data):
        senha = validated_data.pop("senha")
        return Usuario.objects.create_user(
            password=senha,
            papel_sistema="comum",
            **validated_data,
        )


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email", "nome", "papel_sistema", "data_criacao"]
        read_only_fields = ["id", "papel_sistema", "data_criacao"]
