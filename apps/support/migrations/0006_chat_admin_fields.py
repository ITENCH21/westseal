from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0005_supportchatthread_bot_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='supportchatthread',
            name='admin_telegram_chat_id',
            field=models.CharField(
                blank=True, max_length=60,
                help_text='Chat ID в ТГ-группе/личке для уведомлений администраторов',
            ),
        ),
        migrations.AddField(
            model_name='supportchatmessage',
            name='is_bot',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='supportchatmessage',
            name='is_hidden_by_user',
            field=models.BooleanField(
                default=False,
                help_text='Скрыто клиентом (очистка беседы). В БД сохраняется.',
            ),
        ),
        migrations.AlterField(
            model_name='supportchatmessage',
            name='via',
            field=models.CharField(
                max_length=20, default='site',
                help_text='site / telegram / admin / bot',
            ),
        ),
    ]
