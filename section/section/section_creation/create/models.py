import uuid
from django.db import models

class Section(models.Model):
    """
    Represents a classroom or batch section.
    Created by Campus Admin and used by Faculty Coordinators.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    section_name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique name of the section (e.g., A, B, Alpha)"
    )

    class Meta:
        db_table = "sections"
        ordering = ["section_name"]

    def __str__(self):
        return self.section_name
