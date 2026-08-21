from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("imports", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="importbatch",
            name="failure_message",
            field=models.CharField(blank=True, max_length=64, verbose_name="失败安全摘要"),
        ),
    ]
