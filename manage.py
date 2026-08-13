#!/usr/bin/env python
"""Utilidad de linea de comandos de Django para el simulador Buckley-Leverett."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blsim.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. Active el entorno virtual (.venv) "
            "e instale las dependencias con: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
