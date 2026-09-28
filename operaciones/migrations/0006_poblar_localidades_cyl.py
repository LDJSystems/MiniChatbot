import json
from pathlib import Path
from django.db import migrations

def poblar_localidades(apps, schema_editor):
    Provincia = apps.get_model('operaciones', 'Provincia')
    Localidad = apps.get_model('operaciones', 'Localidad')
    
    json_path = Path(__file__).resolve().parent.parent / 'data' / 'localidades_cyl.json'
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for provincia_nombre, localidades in data.items():
        try:
            provincia = Provincia.objects.get(nombre=provincia_nombre)
            for loc_nombre in localidades:
                Localidad.objects.get_or_create(
                    nombre=loc_nombre,
                    provincia=provincia
                )
        except Provincia.DoesNotExist:
            pass

class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0005_merge_20260928_1700'),
    ]

    operations = [
        migrations.RunPython(poblar_localidades),
    ]