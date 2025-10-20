from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
import re
from .models import StringRecord
from .serializers import StringAnalyzeSerializer, StringRecordSerializer
from .utils import analyze_string

# 1️⃣ POST /strings
class StringAnalyzerView(APIView):
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

        response_data = StringRecordSerializer(record).data
        response_data['id'] = record.sha256_hash
        response_data['created_at'] = record.created_at.isoformat()

        return Response(response_data, status=status.HTTP_201_CREATED)

# 2️⃣ GET /strings/{string_value}
class StringDetailView(APIView):
    def get(self, request, value):
        try:
            record = StringRecord.objects.get(value=value)
        except StringRecord.DoesNotExist:
            return Response({"error": "String not found."}, status=status.HTTP_404_NOT_FOUND)

        data = StringRecordSerializer(record).data
        data['id'] = record.sha256_hash
        data['created_at'] = record.created_at.isoformat()

        return Response(data, status=status.HTTP_200_OK)

# 3️⃣ GET /strings (with filters)
class StringListView(APIView):
    def get(self, request):
        params = request.query_params
        filters = Q()
        filters_applied = {}

        #  Filter: is_palindrome
        if 'is_palindrome' in params:
            val = params.get('is_palindrome', '').lower()
            if val in ('true', 'false'):
                filters &= Q(is_palindrome=(val == 'true'))
                filters_applied['is_palindrome'] = (val == 'true')
            else:
                return Response(
                    {"error": "Invalid value for is_palindrome (must be 'true' or 'false')"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        #  Filter: min_length
        if 'min_length' in params:
            try:
                val = int(params['min_length'])
                filters &= Q(length__gte=val)
                filters_applied['min_length'] = val
            except ValueError:
                return Response(
                    {"error": "min_length must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        #  Filter: max_length
        if 'max_length' in params:
            try:
                val = int(params['max_length'])
                filters &= Q(length__lte=val)
                filters_applied['max_length'] = val
            except ValueError:
                return Response(
                    {"error": "max_length must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        #  Filter: word_count
        if 'word_count' in params:
            try:
                val = int(params['word_count'])
                filters &= Q(word_count=val)
                filters_applied['word_count'] = val
            except ValueError:
                return Response(
                    {"error": "word_count must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        #  Filter: contains_character
        if 'contains_character' in params:
            ch = params.get('contains_character')
            if ch and len(ch) == 1:
                filters &= Q(value__icontains=ch)
                filters_applied['contains_character'] = ch
            else:
                return Response(
                    {"error": "contains_character must be a single character."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ✅ Apply all filters (if none provided, returns all)
        queryset = StringRecord.objects.filter(filters).order_by('-created_at')

        # Serialize the data
        serializer = StringRecordSerializer(queryset, many=True)

        # ✅ Return structured response
        return Response({
            "data": serializer.data,
            "count": queryset.count(),
            "filters_applied": filters_applied
        }, status=status.HTTP_200_OK)

# 4️⃣ DELETE /strings/{string_value}
class StringDeleteView(APIView):
    def delete(self, request, value):
        try:
            record = StringRecord.objects.get(value=value)
        except StringRecord.DoesNotExist:
            return Response({"error": "String not found."}, status=status.HTTP_404_NOT_FOUND)
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class NaturalLanguageFilterView(APIView):
    def get(self, request):
        query = request.query_params.get('query', '')
        if not query:
            return Response({"error": "Query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        parsed_filters = {}
        query_lower = query.lower()
 
        # Rule 1: Palindrome detection
        if "palindromic" in query_lower or "palindrome" in query_lower:
            parsed_filters["is_palindrome"] = True

        # Rule 2: Single word or multi-word
        if "single word" in query_lower:
            parsed_filters["word_count"] = 1
        elif "two words" in query_lower:
            parsed_filters["word_count"] = 2
        elif "three words" in query_lower:
            parsed_filters["word_count"] = 3

        # Rule 3: Longer/shorter than N characters
        match_longer = re.search(r"longer than (\d+)", query_lower)
        match_shorter = re.search(r"shorter than (\d+)", query_lower)
        if match_longer:
            parsed_filters["min_length"] = int(match_longer.group(1)) + 1
        if match_shorter:
            parsed_filters["max_length"] = int(match_shorter.group(1)) - 1

        # Rule 4: Contains character
        match_contains = re.search(r"contain(?:ing)? the letter (\w)", query_lower)
        if match_contains:
            parsed_filters["contains_character"] = match_contains.group(1)

        # If no patterns matched
        if not parsed_filters:
            return Response({
                "error": "Unable to parse natural language query",
                "interpreted_query": {"original": query_lower, "parsed_filters": parsed_filters}
            }, status=status.HTTP_400_BAD_REQUEST)

        # Build filters dynamically
        from django.db.models import Q
        filters = Q()
        if "is_palindrome" in parsed_filters:
            filters &= Q(is_palindrome=True)
        if "word_count" in parsed_filters:
            filters &= Q(word_count=parsed_filters["word_count"])
        if "min_length" in parsed_filters:
            filters &= Q(length__gte=parsed_filters["min_length"])
        if "max_length" in parsed_filters:
            filters &= Q(length__lte=parsed_filters["max_length"])
        if "contains_character" in parsed_filters:
            filters &= Q(value__icontains=parsed_filters["contains_character"])

        # Apply filters
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
