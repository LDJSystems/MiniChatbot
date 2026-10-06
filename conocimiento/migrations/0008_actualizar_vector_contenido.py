from django.db import migrations

# SQL que reemplaza la función del trigger para que el vector_busqueda
# se construya SOLO con el campo 'contenido', ignorando el título.
SQL_ACTUALIZAR_FUNCION_TRIGGER = """
CREATE OR REPLACE FUNCTION actualizar_vector_busqueda()
RETURNS trigger AS $$
BEGIN
    NEW.vector_busqueda :=
        setweight(
            to_tsvector('pg_catalog.spanish', COALESCE(NEW.contenido, '')),
            'A'
        );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Regenera los vectores de todos los registros ya existentes en la tabla
# para que reflejen la nueva lógica (solo contenido, sin título).
SQL_REGENERAR_VECTORES = """
UPDATE base_conocimiento
SET vector_busqueda =
    setweight(
        to_tsvector('pg_catalog.spanish', COALESCE(contenido, '')),
        'A'
    );
"""

# Reverse: restaura la función original con título (peso A) + contenido (peso B)
SQL_REVERTIR_FUNCION_TRIGGER = """
CREATE OR REPLACE FUNCTION actualizar_vector_busqueda()
RETURNS trigger AS $$
BEGIN
    NEW.vector_busqueda :=
        setweight(to_tsvector('pg_catalog.spanish', COALESCE(NEW.titulo, '')), 'A') ||
        setweight(to_tsvector('pg_catalog.spanish', COALESCE(NEW.contenido, '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

SQL_REVERTIR_VECTORES = """
UPDATE base_conocimiento
SET vector_busqueda :=
    setweight(to_tsvector('pg_catalog.spanish', COALESCE(titulo, '')), 'A') ||
    setweight(to_tsvector('pg_catalog.spanish', COALESCE(contenido, '')), 'B');
"""


class Migration(migrations.Migration):

    dependencies = [
        ('conocimiento', '0007_alter_baseconocimiento_colectivo_and_more'),
    ]

    operations = [
        # 1. Actualiza la función PL/pgSQL del trigger (para nuevos registros)
        migrations.RunSQL(
            sql=SQL_ACTUALIZAR_FUNCION_TRIGGER,
            reverse_sql=SQL_REVERTIR_FUNCION_TRIGGER,
        ),
        # 2. Regenera los vectores de los registros existentes
        migrations.RunSQL(
            sql=SQL_REGENERAR_VECTORES,
            reverse_sql=SQL_REVERTIR_VECTORES,
        ),
    ]