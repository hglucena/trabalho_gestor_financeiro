from django.core.management.base import BaseCommand

from core.models import Mesada


class Command(BaseCommand):
    help = (
        "Aplica as recargas automáticas de mesada vencidas (semanal/quinzenal/mensal). "
        "A recarga também acontece de forma automática quando a mesada é consultada; "
        "este comando existe para agendamento (cron) e para forçar a atualização em lote."
    )

    def handle(self, *args, **options):
        recarregadas = 0
        for mesada in Mesada.objects.all():
            if mesada.recarregar_se_devido():
                recarregadas += 1
                self.stdout.write(
                    f"  {mesada.dependente.nome}: saldo atualizado para R$ {mesada.saldo_atual}"
                )
        self.stdout.write(self.style.SUCCESS(f"{recarregadas} mesada(s) recarregada(s)."))
