from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Payment', '0013_pricingevent_studentverification_userpricingfeature'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='allow_group_purchase',
            field=models.BooleanField(default=True),
        ),
    ]
