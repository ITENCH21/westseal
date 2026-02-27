from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_add_manufacturer_website_to_catalogpdf"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="sealproduct",
            index=models.Index(fields=["is_active"], name="sealproduct_active_idx"),
        ),
        migrations.AddIndex(
            model_name="sealproduct",
            index=models.Index(fields=["is_active", "category"], name="sealproduct_active_cat_idx"),
        ),
        migrations.AddIndex(
            model_name="sealproduct",
            index=models.Index(fields=["is_active", "subcategory"], name="sealproduct_active_subcat_idx"),
        ),
        migrations.AddIndex(
            model_name="sealproduct",
            index=models.Index(fields=["slug"], name="sealproduct_slug_idx"),
        ),
    ]
