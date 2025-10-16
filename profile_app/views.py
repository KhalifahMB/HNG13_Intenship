from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timezone
from .utils import fetch_cat_fact


class ProfileView(APIView):
    def get(self, request):
        fact, upstream_status = fetch_cat_fact()
        current_time = datetime.now(timezone.utc).isoformat()

        data = {
            "status": "success" if upstream_status == 200 else f"failed-{upstream_status}",
            "user": {
                "email": "muhammadelkufahn27@gmail.com",
                "name": "Muhammad Ahmad El-kufahn",
                "stack": "Python/Django"
            },
            "timestamp": current_time,
            "fact": fact
        }

        # If the upstream service failed, return a 502/503/504 to indicate proxy/upstream issues.
        if upstream_status != 200:
            return Response(data, status=upstream_status)

        return Response(data, status=200)
