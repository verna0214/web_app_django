# Generated by Django 5.1.4 on 2025-01-08 09:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("posts", "0004_alter_tag_options_tag_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="image",
            field=models.FileField(blank=True, null=True, upload_to="icons/"),
        ),
    ]