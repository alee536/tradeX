from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0003_purchase_rejection_date_purchase_rejection_notes_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='purchase',
            name='txid',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True),
        ),
    ]
