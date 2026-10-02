from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leads", "0003_remove_lead_lead_email_o_telefono_alter_lead_email_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lead",
            name="email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AlterField(
            model_name="lead",
            name="telefono",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.RemoveConstraint(
            model_name="lead",
            name="lead_email_o_telefono",
        ),
        migrations.AddConstraint(
            model_name="lead",
            constraint=models.CheckConstraint(
                condition=models.Q(email__gt="") | models.Q(telefono__gt=""),
                name="lead_email_o_telefono",
            ),
        ),
    ]