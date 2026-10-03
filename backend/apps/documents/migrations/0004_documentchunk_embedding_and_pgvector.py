from django.db import migrations
import pgvector.django


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_documentchunk'),
    ]

    operations = [
        # Must execute CREATE EXTENSION vector; requires db superuser or cloud sql equivalent
        pgvector.django.VectorExtension(),
        migrations.AddField(
            model_name='documentchunk',
            name='embedding',
            field=pgvector.django.VectorField(blank=True, dimensions=384, help_text='all-MiniLM-L6-v2 neural embedding vector', null=True),
        ),
    ]
