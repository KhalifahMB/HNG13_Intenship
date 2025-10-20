from django.db import models

class StringRecord(models.Model):
    value = models.TextField(unique=True)
    sha256_hash = models.CharField(
        max_length=64, unique=True)  # sha256 hex length = 64
    length = models.PositiveIntegerField()
    is_palindrome = models.BooleanField()
    unique_characters = models.PositiveIntegerField()
    word_count = models.PositiveIntegerField()
    character_frequency_map = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.value} - {self.sha256_hash[:50]}"
