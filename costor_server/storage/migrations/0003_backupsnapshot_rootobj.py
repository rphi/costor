# Generated by Django 2.2.6 on 2020-04-22 15:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('storage', '0002_auto_20200422_0118'),
    ]

    operations = [
        migrations.AddField(
            model_name='backupsnapshot',
            name='rootobj',
            field=models.CharField(default='', max_length=256),
            preserve_default=False,
        ),
    ]
