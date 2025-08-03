import uuid
from django.db import models
from django.utils import timezone


class ExtractionJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    api_token = models.CharField(max_length=255)
    result_data = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    record_count = models.IntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Job {self.job_id} - {self.status}"

    def duration_seconds(self):
        """Calculate job duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (timezone.now() - self.start_time).total_seconds()
        return 0

    def can_be_cancelled(self):
        """Check if job can be cancelled"""
        return self.status in ['pending', 'in_progress']


class ExtractedRecord(models.Model):
    """Model to store individual extracted records"""
    job = models.ForeignKey(ExtractionJob, on_delete=models.CASCADE, related_name='records')
    id_from_service = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    additional_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id_from_service']
        unique_together = ['job', 'id_from_service']

    def __str__(self):
        return f"{self.email or self.id_from_service} - Job {self.job.job_id}"