import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base: adds created/updated timestamps to every model."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDPrimaryKeyModel(models.Model):
    """Abstract base: UUID primary key instead of auto-increment int.
    Used for anything that may be referenced externally (e.g. in QR payloads)
    where guessable sequential IDs would be a problem.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True
