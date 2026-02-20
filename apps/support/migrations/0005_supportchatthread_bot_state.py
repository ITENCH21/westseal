from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0004_quicklead_supportchatattachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportchatthread',
            name='bot_state',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
