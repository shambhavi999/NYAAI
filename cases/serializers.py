"""
NYAAI - cases/serializers.py
Converts Case data to/from JSON
"""

from rest_framework import serializers
from .models import Case, LegalNotice, CaseTimeline


class CaseTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CaseTimeline
        fields = ['id', 'step', 'description', 'due_date', 'completed', 'order']


class LegalNoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LegalNotice
        fields = ['id', 'version', 'created_at']


class CaseSerializer(serializers.ModelSerializer):
    timeline     = CaseTimelineSerializer(many=True, read_only=True)
    notices      = LegalNoticeSerializer(many=True, read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    status_display   = serializers.CharField(source='get_status_display',   read_only=True)

    class Meta:
        model  = Case
        fields = [
            'id', 'title', 'description', 'category', 'category_display',
            'language', 'status', 'status_display', 'is_analysed',
            'laws_violated', 'forum_type', 'ai_summary', 'confidence_score',
            'documents_needed', 'notice_sent', 'timeline', 'notices',
            'respondent_name', 'respondent_address',
            'created_at', 'updated_at',
        ]


class CaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Case
        fields = ['title', 'description', 'category', 'language',
                  'respondent_name', 'respondent_address']

    def validate_title(self, value):
        if len(value) < 5:
            raise serializers.ValidationError('Title must be at least 5 characters.')
        return value

    def validate_description(self, value):
        if len(value) < 20:
            raise serializers.ValidationError(
                'Please describe your problem in more detail (at least 20 characters).'
            )
        return value