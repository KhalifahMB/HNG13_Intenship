from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime, timezone
from .utils import fetch_cat_fact


class ProfileView(APIView):
    def get(self, request):
        cat_fact = fetch_cat_fact()
        current_time = datetime.now(timezone.utc).isoformat()

        data = {
            "status": "success",
            "user": {
                "email": "muhammadelkufahn27@gmail.com",
                "name": "Muhammad Ahmad El-kufahn",
                "stack": "Python/Django"
            },
            "timestamp": current_time,
            "fact": cat_fact
        }

        return Response(data)
