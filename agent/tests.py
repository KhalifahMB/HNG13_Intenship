from django.test import Client, TestCase
import json


class A2ATests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_simple_explain(self):
        payload = {
            "jsonrpc": "2.0",
            "id": "test-001",
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "role": "user",
                    "parts": [
                        {"kind": "text", "text": "Explain Newton's 2nd law simply"}
                    ],
                    "messageId": "msg-001",
                    "taskId": "task-001",
                }
            },
        }
        resp = self.client.post(
            "/a2a/agent/edusimplify/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("result", data)
        self.assertIn("artifacts", data["result"])
