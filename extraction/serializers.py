from rest_framework import serializers
from .models import ExtractionJob, ExtractedRecord


class ExtractedRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtractedRecord
        fields = ['id_from_service', 'email', 'first_name', 'last_name', 'additional_data']


class ExtractionJobSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.ReadOnlyField()
    
    class Meta:
        model = ExtractionJob
        fields = ['job_id', 'status', 'record_count', 'start_time', 'end_time', 
                 'created_at', 'updated_at', 'error_message', 'duration_seconds']
        read_only_fields = ['job_id', 'created_at', 'updated_at']


class JobStartSerializer(serializers.Serializer):
    api_token = serializers.CharField(max_length=255, help_text="API token for the third-party service")


class JobStatusSerializer(serializers.ModelSerializer):
    duration_seconds = serializers.ReadOnlyField()
    
    class Meta:
        model = ExtractionJob
        fields = ['job_id', 'status', 'record_count', 'start_time', 'end_time', 
                 'created_at', 'updated_at', 'error_message', 'duration_seconds']


class JobStatisticsSerializer(serializers.Serializer):
    total_jobs = serializers.IntegerField()
    completed_jobs = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()
    pending_jobs = serializers.IntegerField()
    in_progress_jobs = serializers.IntegerField()
    cancelled_jobs = serializers.IntegerField()
    average_duration_seconds = serializers.FloatField()
    total_records_extracted = serializers.IntegerField()


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    timestamp = serializers.DateTimeField()
    version = serializers.CharField(default="1.0.0")