from django.db import migrations

def poblar_provincias(apps, schema_editor):
    Provincia = apps.get_model('operaciones', 'Provincia')
    provincias_cyl = [
        {"nombre": "Ávila", "codigo": "05"},
        {"nombre": "Burgos", "codigo": "09"},
        {"nombre": "León", "codigo": "24"},
        {"nombre": "Palencia", "codigo": "34"},
        {"nombre": "Salamanca", "codigo": "37"},
        {"nombre": "Segovia", "codigo": "40"},
        {"nombre": "Soria", "codigo": "42"},
        {"nombre": "Valladolid", "codigo": "47"},
        {"nombre": "Zamora", "codigo": "49"},
    ]
    for p in provincias_cyl:
        Provincia.objects.get_or_create(nombre=p["nombre"], defaults={"codigo": p["codigo"]})

def revertir_provincias(apps, schema_editor):
    Provincia = apps.get_model('operaciones', 'Provincia')
    Provincia.objects.filter(codigo__in=["05", "09", "24", "34", "37", "40", "42", "47", "49"]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0001_initial'), # Ajusta según tu última migración
    ]

    operations = [
        migrations.RunPython(poblar_provincias, revertir_provincias),
    ]