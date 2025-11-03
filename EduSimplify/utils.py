import os
from google import genai
from django.conf import settings
from rest_framework import status


def _get_genai_client():
    """Lazily create and return a genai client with explicit error when missing config."""
    api_key = getattr(settings, "GEMINI_API_KEY", None) or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini API key not configured (GEMINI_API_KEY)")
    return genai.Client(api_key=api_key)


def ask_gemini(prompt, model="gemini-2.5-flash"):
    """Call Google's GenAI client to generate a text response.

    Returns a plain string on success. Raises RuntimeError on known problems so
    callers can catch and convert into appropriate HTTP errors.
    """
    client = _get_genai_client()
    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        # Surface a clear error that the view can handle
        raise RuntimeError(f"genai request failed: {exc}") from exc

    # Different genai client versions may expose the text differently.
    # Try common accessors then fall back to str(response).
    text = None
    if hasattr(response, "text"):
        text = getattr(response, "text")
    elif isinstance(response, dict):
        # try to extract from dict structure
        text = response.get("text") or response.get("responseText")
    else:
        # last resort
        text = str(response)

    if not text:
        raise RuntimeError("genai returned empty response")

    return text


def make_a2a_success(request_id, result_obj):
    """Return a JSON-RPC 2.0 + A2A-style success payload dict.

    The view should return (payload_dict, http_status_code).
    """
    return {"jsonrpc": "2.0", "id": request_id, "result": result_obj}, status.HTTP_200_OK


def make_a2a_error(request_id, code, message, data=None, http_status=status.HTTP_400_BAD_REQUEST):
    payload = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    if data is not None:
        payload["error"]["data"] = data
    return payload, http_status
