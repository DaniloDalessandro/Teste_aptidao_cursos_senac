# Generated by Django 4.2.3 on 2023-07-24 02:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interviews', '0002_message'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chat',
            name='title',
            field=models.CharField(editable=False, max_length=100, verbose_name='Título'),
        ),
    ]
