from django.db import migrations, models

TAUX_CHOICES = [
    (0, "0 % (exonéré / débours)"), (7, "7 %"), (10, "10 %"), (14, "14 %"), (20, "20 %"),
]


class Migration(migrations.Migration):
    """Add a VAT rate per line.

    Lines that already exist were issued without VAT: they get 0 % so that the totals
    of past quotes and invoices (and the balances already paid against them) do not
    change. New lines default to 20 %.
    """

    dependencies = [
        ("billing", "0002_payment_compte"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceline",
            name="taux_tva",
            field=models.PositiveSmallIntegerField(choices=TAUX_CHOICES, default=0, verbose_name="TVA"),
        ),
        migrations.AddField(
            model_name="quoteline",
            name="taux_tva",
            field=models.PositiveSmallIntegerField(choices=TAUX_CHOICES, default=0, verbose_name="TVA"),
        ),
        migrations.AlterField(
            model_name="invoiceline",
            name="taux_tva",
            field=models.PositiveSmallIntegerField(choices=TAUX_CHOICES, default=20, verbose_name="TVA"),
        ),
        migrations.AlterField(
            model_name="quoteline",
            name="taux_tva",
            field=models.PositiveSmallIntegerField(choices=TAUX_CHOICES, default=20, verbose_name="TVA"),
        ),
        migrations.AlterField(
            model_name="invoiceline",
            name="prix_unitaire",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Prix unitaire HT"),
        ),
        migrations.AlterField(
            model_name="quoteline",
            name="prix_unitaire",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="Prix unitaire HT"),
        ),
    ]
