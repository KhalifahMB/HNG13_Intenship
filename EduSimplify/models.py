# agent/models.py
from django.db import models
import uuid


def gen_uuid():
    return str(uuid.uuid4())


class Conversation(models.Model):
    context_id = models.CharField(max_length=64, unique=True, default=gen_uuid)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.context_id


class Message(models.Model):
    message_id = models.CharField(max_length=64, unique=False, default=gen_uuid)
    context = models.ForeignKey(
        Conversation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="messages",
    )
    role = models.CharField(max_length=16)  # 'user'|'agent'|'system'
    parts = (
        models.JSONField()
    )  # list of parts: [{kind: text/data/file, text:..., data:...}]
    task_id = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role}:{self.message_id}"


class Artifact(models.Model):
    artifact_id = models.CharField(max_length=64, unique=True, default=gen_uuid)
    context = models.ForeignKey(
        Conversation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="artifacts",
    )
    name = models.CharField(max_length=128)
    parts = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}:{self.artifact_id}"
