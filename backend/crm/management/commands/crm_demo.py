from django.core.management.base import BaseCommand

from crm import demo


class Command(BaseCommand):
    help = "Carga los datos de demostración del CRM (Kusi Hogar S.A.C., empresa ficticia). Sin --reiniciar solo actúa si está vacío."

    def add_arguments(self, parser):
        parser.add_argument("--reiniciar", action="store_true", help="Borra clientes, productos y entrenamiento y los vuelve a crear")

    def handle(self, *args, **opts):
        r = demo.cargar(reiniciar=opts["reiniciar"])
        if not r["cargado"]:
            self.stdout.write("CRM: ya tiene datos, no se cambia nada.")
            return
        self.stdout.write(f"CRM: demo cargada con {r['clientes']} clientes y {r['mensajes']} mensajes.")
        if r.get("clave_generada"):
            self.stdout.write(f"CRM: no hay CRM_CLAVE_DEMO; clave generada para las cuentas demo: {r['clave_generada']}")
