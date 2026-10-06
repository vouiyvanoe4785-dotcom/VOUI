from django.db import migrations, models

TAUX_CHOICES = [
    (0, "0 % (exonéré / débours)"), (7, "7 %"), (10, "10 %"), (14, "14 %"), (20, "20 %"),
]


class Migration(migrations.Migration):
    """VAT rate on supplier invoice lines.

    Existing lines get 0 % so the totals and balances already recorded (and paid) do not
    change; new lines default to 20 %.
    """

    dependencies = [
        ("purchasing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplierinvoiceline",
            name="taux_tva",
            field=models.PositiveSmallIntegerField(choices=TAUX_CHOICES, default=0, verbose_name="TVA"),
        ),
        migrations.AlterField(
            model_name="supplierinvoiceline",
            name="taux_tva",
            field=models.PositiveSmallIntegerField(choices=TAUX_CHOICES, default=20, verbose_name="TVA"),
        ),
        migrations.AlterField(
            model_name="supplierinvoiceline",
            name="prix_unitaire",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Prix unitaire HT"),
        ),
    ]
