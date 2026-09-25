from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('conocimiento', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION fn_bc_actualizar_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.vector_busqueda := 
                    setweight(to_tsvector('pg_catalog.spanish', coalesce(NEW.titulo, '')), 'A') ||
                    setweight(to_tsvector('pg_catalog.spanish', coalesce(NEW.contenido, '')), 'B');
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS tg_bc_actualizar_vector ON base_conocimiento;

            CREATE TRIGGER tg_bc_actualizar_vector
            BEFORE INSERT OR UPDATE ON base_conocimiento
            FOR EACH ROW
            EXECUTE FUNCTION fn_bc_actualizar_vector();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS tg_bc_actualizar_vector ON base_conocimiento;
            DROP FUNCTION IF EXISTS fn_bc_actualizar_vector();
            """
        ),
    ]