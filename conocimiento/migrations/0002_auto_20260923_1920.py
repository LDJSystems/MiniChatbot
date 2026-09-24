from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('conocimiento', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE base_conocimiento ALTER COLUMN vector_busqueda TYPE tsvector USING to_tsvector('pg_catalog.spanish', COALESCE(titulo,'') || ' ' || COALESCE(contenido,''));

            CREATE OR REPLACE FUNCTION tg_bc_actualizar_vector_func() RETURNS trigger AS $$
            BEGIN
                NEW.vector_busqueda := setweight(to_tsvector('pg_catalog.spanish', NEW.titulo), 'A') || setweight(to_tsvector('pg_catalog.spanish', NEW.contenido), 'B');
                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER tg_bc_actualizar_vector
            BEFORE INSERT OR UPDATE ON base_conocimiento
            FOR EACH ROW
            EXECUTE FUNCTION tg_bc_actualizar_vector_func();

            CREATE INDEX idx_bc_vector_gin ON base_conocimiento USING gin (vector_busqueda);
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS tg_bc_actualizar_vector ON base_conocimiento;
            DROP FUNCTION IF EXISTS tg_bc_actualizar_vector_func();
            DROP INDEX IF EXISTS idx_bc_vector_gin;
            ALTER TABLE base_conocimiento ALTER COLUMN vector_busqueda TYPE text USING vector_busqueda::text;
            """
        ),
    ]