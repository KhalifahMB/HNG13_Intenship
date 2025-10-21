from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers, generics
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import re
from .models import StringRecord
from .serializers import StringAnalyzeSerializer, StringRecordSerializer
from .utils import analyze_string
from .filters import StringRecordFilter

# 1️⃣ POST & GET /strings


class StringAnalyzerView(generics.ListAPIView, APIView):
    queryset = StringRecord.objects.all().order_by('-created_at')
    serializer_class = StringRecordSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = StringRecordFilter

    @swagger_auto_schema(
        request_body=StringAnalyzeSerializer,
        operation_summary="Analyze and store a new string",
    )
    def post(self, request):
        serializer = StringAnalyzeSerializer(data=request.data)
        if not serializer.is_valid():
            code = serializer.errors.get('non_field_errors', [''])[0]
            if code == 'conflict':
                return Response({"error": "String already exists."}, status=status.HTTP_409_CONFLICT)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            record = serializer.save()
        except serializers.ValidationError as e:
            return Response({"error": str(e.detail)}, status=status.HTTP_409_CONFLICT)

        # Serializer now returns the desired representation
        return Response(StringRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="List all analyzed strings",
        manual_parameters=[
            openapi.Parameter(
                "is_palindrome",
                openapi.IN_QUERY,
                description="Filter by palindrome (true/false)",
                type=openapi.TYPE_BOOLEAN,
            ),
            openapi.Parameter(
                "min_length",
                openapi.IN_QUERY,
                description="Minimum string length",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "max_length",
                openapi.IN_QUERY,
                description="Maximum string length",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "word_count",
                openapi.IN_QUERY,
                description="Exact word count",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "contains_character",
                openapi.IN_QUERY,
                description="Filter strings that contain this character",
                type=openapi.TYPE_STRING,
            ),
        ],

    )
    def get(self, request, *args, **kwargs):
        filtered_queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(filtered_queryset, many=True)

        return Response({
            "data": serializer.data,
            "count": filtered_queryset.count(),
            "filters_applied": request.query_params.dict(),
        }, status=status.HTTP_200_OK)

# 2️⃣ GET &  DELETE  /strings/{string_value}


class StringDetailView(APIView):

    def get(self, request, value):
        try:
            record = StringRecord.objects.get(value=value)
        except StringRecord.DoesNotExist:
            return Response({"error": "String not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(StringRecordSerializer(record).data, status=status.HTTP_200_OK)

    def delete(self, request, value):
        try:
            record = StringRecord.objects.get(value=value)
        except StringRecord.DoesNotExist:
            return Response({"error": "String not found."}, status=status.HTTP_404_NOT_FOUND)
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# 4️⃣ GET /strings/filter-by-natural-language

class NaturalLanguageFilterView(APIView):
    @swagger_auto_schema(
        operation_summary="Filter analyzed strings using natural language queries",
        manual_parameters=[
            openapi.Parameter(
                "query",
                openapi.IN_QUERY,
                description="Natural language query, e.g. 'all single word palindromic strings'",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
    )
    def get(self, request):
        query = request.query_params.get("query", "")
        if not query:
            return Response(
                {"error": "Query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        query_lower = query.lower()
        parsed_filters = {}

        # ✅ Rule 1: Detect palindrome-related queries
        if "palindromic" in query_lower or "palindrome" in query_lower:
            parsed_filters["is_palindrome"] = True

        # ✅ Rule 2: Detect number of words
        if "single word" in query_lower:
            parsed_filters["word_count"] = 1
        elif "two words" in query_lower:
            parsed_filters["word_count"] = 2
        elif "three words" in query_lower:
            parsed_filters["word_count"] = 3
        elif "word count of" in query_lower:
            match = re.search(r"word count of (\d+)", query_lower)
            if match:
                parsed_filters["word_count"] = int(match.group(1))

        # ✅ Rule 3: Handle "longer than" and "shorter than"
        match_longer = re.search(r"longer than (\d+)", query_lower)
        match_shorter = re.search(r"shorter than (\d+)", query_lower)
        if match_longer:
            parsed_filters["min_length"] = int(match_longer.group(1)) + 1
        if match_shorter:
            parsed_filters["max_length"] = int(match_shorter.group(1)) - 1

        # ✅ Rule 4: Handle "containing the letter X"
        match_contains = re.search(r"contain(?:ing)? the letter (\w)", query_lower)
        if match_contains:
            parsed_filters["contains_character"] = match_contains.group(1)

        # ✅ Rule 5: Handle heuristic for “first vowel” phrase
        if "first vowel" in query_lower:
            parsed_filters["contains_character"] = "a"

        # ✅ If no valid patterns matched
        if not parsed_filters:
            return Response({
                "error": "Unable to parse natural language query.",
                "interpreted_query": {
                    "original": query,
                    "parsed_filters": parsed_filters
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Detect conflicting filters (e.g. min_length > max_length)
        if (
            "min_length" in parsed_filters
            and "max_length" in parsed_filters
            and parsed_filters["min_length"] > parsed_filters["max_length"]
        ):
            return Response({
                "error": "Conflicting filters detected: min_length cannot be greater than max_length.",
                "interpreted_query": {
                    "original": query,
                    "parsed_filters": parsed_filters
                }
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        # ✅ Build QuerySet filters dynamically
        filters = Q()
        if parsed_filters.get("is_palindrome"):
            filters &= Q(is_palindrome=True)
        if parsed_filters.get("word_count") is not None:
            filters &= Q(word_count=parsed_filters["word_count"])
        if parsed_filters.get("min_length") is not None:
            filters &= Q(length__gte=parsed_filters["min_length"])
        if parsed_filters.get("max_length") is not None:
            filters &= Q(length__lte=parsed_filters["max_length"])
        if parsed_filters.get("contains_character"):
            filters &= Q(value__icontains=parsed_filters["contains_character"])

        # ✅ Query the database
        strings = StringRecord.objects.filter(filters)
        serialized = StringRecordSerializer(strings, many=True)

        return Response({
            "data": serialized.data,
            "count": strings.count(),
            "interpreted_query": {
                "original": query,
                "parsed_filters": parsed_filters
            }
        }, status=status.HTTP_200_OK)
