from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from core.models import ContaAPagar, Orcamento, Transacao, Usuario


class Command(BaseCommand):
    help = (
        "Envia lembretes por e-mail: contas a pagar vencendo (ou vencidas) "
        "e orçamentos pessoais estourados. Use EMAIL_BACKEND para configurar o envio real; "
        "por padrão os e-mails são impressos no console."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=3,
            help="Janela de antecedência do vencimento em dias (padrão: 3).",
        )

    def handle(self, *args, **options):
        hoje = timezone.localdate()
        limite = hoje + timedelta(days=options["dias"])
        enviados = 0

        for usuario in Usuario.objects.filter(is_active=True, papel_sistema="comum"):
            avisos = []

            contas = ContaAPagar.objects.filter(
                usuario=usuario, pago=False, vencimento__lte=limite
            ).order_by("vencimento")
            for conta in contas:
                situacao = "VENCIDA" if conta.vencimento < hoje else f"vence em {conta.vencimento:%d/%m/%Y}"
                avisos.append(f"- Conta a pagar: {conta.descricao} (R$ {conta.valor}) — {situacao}")

            orcamentos = Orcamento.objects.filter(usuario=usuario).select_related("categoria")
            for orcamento in orcamentos:
                realizado = Transacao.objects.filter(
                    usuario=usuario,
                    categoria=orcamento.categoria,
                    tipo="despesa",
                    data__year=orcamento.periodo.year,
                    data__month=orcamento.periodo.month,
                ).aggregate(total=Sum("valor"))["total"] or 0
                if realizado > orcamento.valor_limite:
                    avisos.append(
                        f"- Orçamento estourado: {orcamento.categoria.nome} "
                        f"(limite R$ {orcamento.valor_limite}, gasto R$ {realizado})"
                    )

            if not avisos:
                continue

            send_mail(
                subject="NossoBolso — seus lembretes financeiros",
                message=f"Olá, {usuario.nome}!\n\n" + "\n".join(avisos) + "\n\n— NossoBolso",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=False,
            )
            enviados += 1

        self.stdout.write(self.style.SUCCESS(f"{enviados} lembrete(s) enviado(s)."))
