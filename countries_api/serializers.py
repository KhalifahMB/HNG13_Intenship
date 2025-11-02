from rest_framework import serializers
from .models import Country, RefreshMetadata


class CountrySerializer(serializers.ModelSerializer):
    """
    Serializer for Country model with all fields
    """
    class Meta:
        model = Country
        fields = [
            'id',
            'name',
            'capital',
            'region',
            'population',
            'currency_code',
            'exchange_rate',
            'estimated_gdp',
            'flag_url',
            'last_refreshed_at'
        ]
        read_only_fields = ['id', 'last_refreshed_at']

    def validate_name(self, value):
        """
        Validate that name is not empty
        """
        if not value or not value.strip():
            raise serializers.ValidationError("Name is required and cannot be empty")
        return value.strip()

    def validate_population(self, value):
        """
        Validate that population is a positive number
        """
        if value is None:
            raise serializers.ValidationError("Population is required")
        if value < 0:
            raise serializers.ValidationError("Population must be a positive number")
        return value

    def validate(self, data):
        """
        Object-level validation
        """
        # Check required fields
        if 'name' not in data or not data.get('name'):
            raise serializers.ValidationError({
                "name": "is required"
            })

        if 'population' not in data or data.get('population') is None:
            raise serializers.ValidationError({
                "population": "is required"
            })

        return data


class CountryListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing countries
    """
    class Meta:
        model = Country
        fields = [
            'id',
            'name',
            'capital',
            'region',
            'population',
            'currency_code',
            'exchange_rate',
            'estimated_gdp',
            'flag_url',
            'last_refreshed_at'
        ]


class RefreshMetadataSerializer(serializers.ModelSerializer):
    """
    Serializer for RefreshMetadata model
    """
    class Meta:
        model = RefreshMetadata
        fields = ['total_countries', 'last_refreshed_at', 'refresh_status']


class StatusResponseSerializer(serializers.Serializer):
    """
    Serializer for status endpoint response
    """
    total_countries = serializers.IntegerField()
    last_refreshed_at = serializers.DateTimeField(allow_null=True)


class ErrorResponseSerializer(serializers.Serializer):
    """
    Serializer for error responses
    """
    error = serializers.CharField()
    # details can be a string message or a mapping. Keep it permissive for existing
    # responses.
    details = serializers.JSONField(required=False)


class RefreshResponseSerializer(serializers.Serializer):
    """
    Serializer for refresh endpoint response
    """
    message = serializers.CharField()
    started_at = serializers.CharField()
