from rest_framework import serializers
from .models import StringRecord
from .utils import analyze_string


class StringRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = StringRecord
        # keep model fields defined, but we'll present a custom representation
        fields = '__all__'
        read_only_fields = ['sha256_hash', 'length', 'is_palindrome',
                            'unique_characters', 'word_count', 'character_frequency_map', 'created_at']

    def to_representation(self, instance):
        props = {
            'length': instance.length,
            'is_palindrome': instance.is_palindrome,
            'unique_characters': instance.unique_characters,
            'word_count': instance.word_count,
            'sha256_hash': instance.sha256_hash,
            'character_frequency_map': instance.character_frequency_map,
        }

        return {
            'id': instance.sha256_hash,
            'value': instance.value,
            'properties': props,
            'created_at': instance.created_at.isoformat() if getattr(instance, 'created_at', None) is not None else None,
        }


class StringAnalyzeSerializer(serializers.Serializer):
    value = serializers.CharField()

    def validate_value(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError("Value must be a string.")
        return value

    def create(self, validated_data):
        value = validated_data['value']
        from .models import StringRecord

        # Check if already exists
        if StringRecord.objects.filter(value=value).exists():
            raise serializers.ValidationError(
                "String already exists.", code='conflict')

        props = analyze_string(value)
        record = StringRecord.objects.create(
            value=value,
            sha256_hash=props['sha256_hash'],
            length=props['length'],
            is_palindrome=props['is_palindrome'],
            unique_characters=props['unique_characters'],
            word_count=props['word_count'],
            character_frequency_map=props['character_frequency_map'],
        )
        return record
