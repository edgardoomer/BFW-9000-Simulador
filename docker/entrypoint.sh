#!/bin/sh
# Prepara la base antes de levantar el servidor.
set -e

echo "  BFW-9000 · preparando la base de datos..."
python manage.py migrate --noinput

# Siembra los ejemplos solo la primera vez, para no pisar datos del usuario.
PROYECTOS=$(python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blsim.settings')
django.setup()
from core.models import Proyecto
print(Proyecto.objects.count())
" 2>/dev/null || echo 0)

if [ "$PROYECTOS" = "0" ]; then
  echo "  Base vacia: cargando los proyectos de ejemplo..."
  python manage.py cargar_ejemplos
else
  echo "  $PROYECTOS proyecto(s) en la base, no se toca nada."
fi

echo "  Listo. http://localhost:8017"
exec "$@"
