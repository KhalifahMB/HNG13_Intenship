# agent/views.py
import uuid
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    JSONRPCRequestSerializer,
    MessageParamsSerializer,
    ExecuteParamsSerializer,
    A2AMessageSerializer,
)
from .utils import ask_gemini
from .models import Conversation, Message, Artifact


def gen_uuid():
    return str(uuid.uuid4())


class A2AAgentView(APIView):
    """
    POST /a2a/agent/edusimplify/
    Accepts JSON-RPC 2.0 A2A messages and returns JSON-RPC 2.0 responses.
    """

    def post(self, request, *args, **kwargs):
        raw = request.data or {}
        # Validate top-level JSON-RPC fields
        top_serializer = JSONRPCRequestSerializer(data=raw)
        if not top_serializer.is_valid():
            return Response(
                {
                    "jsonrpc": "2.0",
                    "id": raw.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request",
                        "data": top_serializer.errors,
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = top_serializer.validated_data
        request_id = data["id"]
        method = data["method"]

        # Parse params according to method
        params = raw.get("params", {}) or {}
        messages_list = []
        context_id = None
        task_id = None

        try:
            if method == "message/send":
                pser = MessageParamsSerializer(data=params)
                pser.is_valid(raise_exception=True)
                msg = pser.validated_data["message"]
                # Wrap single message into list
                messages_list = [msg]
            elif method == "execute":
                pser = ExecuteParamsSerializer(data=params)
                pser.is_valid(raise_exception=True)
                context_id = pser.validated_data.get("contextId")
                task_id = pser.validated_data.get("taskId")
                messages_list = pser.validated_data.get("messages", [])
            else:
                return Response(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32601, "message": "Method not found"},
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params",
                        "data": str(e),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract user text (last message text parts concatenated)
        try:
            user_texts = []
            for msg in messages_list:
                parts = msg.get("parts", [])  # list of dicts
                text = "\n".join(
                    p.get("text", "") for p in parts if p.get("kind") == "text"
                ).strip()
                user_texts.append(
                    {
                        "role": msg.get("role", "user"),
                        "text": text,
                        "messageId": msg.get("messageId") or gen_uuid(),
                        "taskId": msg.get("taskId") or task_id or gen_uuid(),
                    }
                )
            if not user_texts:
                raise ValueError("No user message parts found")
            last = user_texts[-1]
            user_prompt = last["text"]
        except Exception as exc:
            return Response(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid message format",
                        "data": str(exc),
                    },
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Persist conversation & incoming message
        conv = None
        if context_id:
            conv, _ = Conversation.objects.get_or_create(context_id=context_id)
        else:
            conv = Conversation.objects.create()

        # Save incoming user message
        incoming_msg = Message.objects.create(
            message_id=last["messageId"],
            context=conv,
            role=last["role"],
            parts=[{"kind": "text", "text": user_prompt}],
            task_id=last["taskId"],
        )

        # Build Gemini prompt
        prompt = (
            "You are EduSimplify — a friendly tutor. Answer concisely.\n\n"
            "Task: Explain the following concept in 2-3 simple sentences, give one real-world example, "
            "and a one-line formula or note if applicable.\n\n"
            f"Concept: {user_prompt}\n\nAnswer:"
        )

        # Call Gemini
        try:
            explanation = ask_gemini(prompt)
        except Exception as exc:
            return Response(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": "Internal error contacting LLM",
                        "data": str(exc),
                    },
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Save agent reply message & artifact
        agent_message_id = gen_uuid()
        agent_task_id = last["taskId"]
        Message.objects.create(
            message_id=agent_message_id,
            context=conv,
            role="agent",
            parts=[{"kind": "text", "text": explanation}],
            task_id=agent_task_id,
        )
        artifact = Artifact.objects.create(
            artifact_id=gen_uuid(),
            context=conv,
            name="EduSimplifyResponse",
            parts=[{"kind": "text", "text": explanation}],
        )

        # Build history (incoming + agent)
        history = [
            {
                "kind": "message",
                "role": last["role"],
                "parts": [{"kind": "text", "text": user_prompt}],
                "messageId": last["messageId"],
                "taskId": last["taskId"],
            },
            {
                "kind": "message",
                "role": "agent",
                "parts": [{"kind": "text", "text": explanation}],
                "messageId": agent_message_id,
                "taskId": agent_task_id,
            },
        ]

        # Build result per A2A sample
        result = {
            "id": agent_task_id,
            "contextId": conv.context_id,
            "status": {
                "state": "completed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": {
                    "messageId": agent_message_id,
                    "role": "agent",
                    "parts": [{"kind": "text", "text": explanation}],
                    "kind": "message",
                },
            },
            "artifacts": [
                {
                    "artifactId": artifact.artifact_id,
                    "name": artifact.name,
                    "parts": artifact.parts,
                }
            ],
            "history": history,
            "kind": "task",
        }

        return Response(
            {"jsonrpc": "2.0", "id": request_id, "result": result},
            status=status.HTTP_200_OK,
        )
