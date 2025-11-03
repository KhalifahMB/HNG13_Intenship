# agent/serializers.py
from rest_framework import serializers
from typing import List


class MessagePartSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["text", "data", "file"])
    text = serializers.CharField(allow_blank=True, required=False)
    data = serializers.JSONField(required=False)
    file_url = serializers.URLField(required=False)


class A2AMessageSerializer(serializers.Serializer):
    kind = serializers.CharField(default="message")
    role = serializers.ChoiceField(choices=["user", "agent", "system"])
    parts = MessagePartSerializer(many=True)
    messageId = serializers.CharField(required=False, allow_blank=True)
    taskId = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class MessageConfigurationSerializer(serializers.Serializer):
    blocking = serializers.BooleanField(default=True)


class MessageParamsSerializer(serializers.Serializer):
    message = A2AMessageSerializer()
    configuration = MessageConfigurationSerializer(
        required=False, default={"blocking": True}
    )


class ExecuteParamsSerializer(serializers.Serializer):
    contextId = serializers.CharField(required=False, allow_blank=True)
    taskId = serializers.CharField(required=False, allow_blank=True)
    messages = A2AMessageSerializer(many=True)


class JSONRPCRequestSerializer(serializers.Serializer):
    jsonrpc = serializers.CharField()
    id = serializers.CharField()
    method = serializers.ChoiceField(choices=["message/send", "execute"])
    params = serializers.JSONField()  # validate manually depending on method
