from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('conocimiento', '0003_baseconocimiento_localidad_stagingcursos_localidad_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='baseconocimiento',
            name='url_oficial',
            field=models.TextField(
                blank=True,
                null=True,
                unique=True,
            ),
        ),
    ]