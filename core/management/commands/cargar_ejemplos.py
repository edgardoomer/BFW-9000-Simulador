from django.core.management.base import BaseCommand

from core import engine, seeds


class Command(BaseCommand):
    help = "Carga los dos proyectos de ejemplo y calcula sus resultados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mantener", action="store_true",
            help="No borra los proyectos de ejemplo existentes.",
        )

    def handle(self, *args, **opts):
        proyectos = seeds.crear_todos(reemplazar=not opts["mantener"])
        for p in proyectos:
            datos = engine.analizar_proyecto(p)
            self.stdout.write(self.style.SUCCESS(
                f"{p.id_proyecto}  {p.nombre}"
            ))
            self.stdout.write(
                f"   {p.n_inyectores} inyector(es), {p.n_productores} productor(es), "
                f"{p.pares.count()} canales"
            )
            for fila in datos["orden_irrupcion"]:
                self.stdout.write(
                    f"   {fila['orden']}. {fila['nombre']:<12} "
                    f"L = {fila['L']:>6} ft   k = {fila['k']:>5} md   "
                    f"tBT = {fila['tbt']:>9} d   desde {fila['inyector']}"
                )
            for aviso in datos["avisos"]:
                self.stdout.write(self.style.WARNING("   ! " + aviso))
            self.stdout.write("")
