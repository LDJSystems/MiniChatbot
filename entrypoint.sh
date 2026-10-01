echo "Ejecutando migraciones..."
python manage.py migrate --noinput

echo "Creando tabla de caché para DatabaseCache..."
python manage.py createcachetable

echo "Iniciando servidor..."
exec "$@"