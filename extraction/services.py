import time
import random
from typing import List, Dict, Any
from django.utils import timezone
from .models import ExtractionJob, ExtractedRecord


class MockThirdPartyAPI:
    """
    Mock third-party API for testing purposes.
    In a real implementation, this would integrate with the actual service API.
    """
    
    def __init__(self, api_token: str):
        self.api_token = api_token
    
    def validate_token(self) -> bool:
        """Validate the API token"""
        # Mock validation - in real implementation, make API call to validate
        return bool(self.api_token and len(self.api_token) > 10 and not self.api_token.startswith('invalid'))
    
    def extract_data(self) -> List[Dict[str, Any]]:
        """Extract data from third-party service"""
        if not self.validate_token():
            raise ValueError("Invalid API token")
        
        # Simulate API delay
        time.sleep(random.uniform(1, 3))
        
        # Mock extracted data
        mock_data = [
            {
                "id_from_service": f"user_{i}",
                "email": f"user{i}@example.com",
                "first_name": f"FirstName{i}",
                "last_name": f"LastName{i}",
                "additional_data": {
                    "phone": f"+1-555-{1000 + i:04d}",
                    "company": f"Company {i}",
                    "created_date": "2023-01-01"
                }
            }
            for i in range(1, random.randint(5, 25))
        ]
        
        return mock_data


class ExtractionService:
    """Service to handle data extraction operations"""
    
    @staticmethod
    def start_extraction(api_token: str) -> ExtractionJob:
        """Start a new extraction job"""
        # Create the job
        job = ExtractionJob.objects.create(
            api_token=api_token,
            status='pending'
        )
        
        # In a real implementation, this would be handled by a task queue like Celery
        # For testing purposes, we'll leave jobs in pending state until explicitly processed
        # ExtractionService._process_extraction(job.job_id)
        
        return job
    
    @staticmethod
    def _process_extraction(job_id: str):
        """Process the extraction (this would typically run in background)"""
        try:
            job = ExtractionJob.objects.get(job_id=job_id)
            job.status = 'in_progress'
            job.start_time = timezone.now()
            job.save()
            
            # Initialize the third-party API client
            api_client = MockThirdPartyAPI(job.api_token)
            
            # Extract data
            extracted_data = api_client.extract_data()
            
            # Store extracted records
            records = []
            for data in extracted_data:
                record = ExtractedRecord(
                    job=job,
                    id_from_service=data['id_from_service'],
                    email=data.get('email', ''),
                    first_name=data.get('first_name', ''),
                    last_name=data.get('last_name', ''),
                    additional_data=data.get('additional_data', {})
                )
                records.append(record)
            
            ExtractedRecord.objects.bulk_create(records)
            
            # Update job status
            job.status = 'completed'
            job.end_time = timezone.now()
            job.record_count = len(records)
            job.save()
            
        except ValueError as e:
            # Invalid token or API error
            job.status = 'failed'
            job.error_message = str(e)
            job.end_time = timezone.now()
            job.save()
        except Exception as e:
            # Unexpected error
            job.status = 'failed'
            job.error_message = f"Unexpected error: {str(e)}"
            job.end_time = timezone.now()
            job.save()
    
    @staticmethod
    def cancel_job(job_id: str) -> bool:
        """Cancel a job if it's in a cancellable state"""
        try:
            job = ExtractionJob.objects.get(job_id=job_id)
            if job.can_be_cancelled():
                job.status = 'cancelled'
                job.end_time = timezone.now()
                job.save()
                return True
            return False
        except ExtractionJob.DoesNotExist:
            return False
    
    @staticmethod
    def remove_job_data(job_id: str) -> bool:
        """Remove all data associated with a job"""
        try:
            job = ExtractionJob.objects.get(job_id=job_id)
            # Delete associated records first
            job.records.all().delete()
            # Delete the job itself
            job.delete()
            return True
        except ExtractionJob.DoesNotExist:
            return False
    
    @staticmethod
    def get_job_statistics() -> Dict[str, Any]:
        """Get overall job statistics"""
        from django.db.models import Avg, Sum
        
        total_jobs = ExtractionJob.objects.count()
        completed_jobs = ExtractionJob.objects.filter(status='completed').count()
        failed_jobs = ExtractionJob.objects.filter(status='failed').count()
        pending_jobs = ExtractionJob.objects.filter(status='pending').count()
        in_progress_jobs = ExtractionJob.objects.filter(status='in_progress').count()
        cancelled_jobs = ExtractionJob.objects.filter(status='cancelled').count()
        
        # Calculate average duration for completed jobs
        completed_job_durations = []
        for job in ExtractionJob.objects.filter(status='completed', start_time__isnull=False, end_time__isnull=False):
            completed_job_durations.append(job.duration_seconds())
        
        avg_duration = sum(completed_job_durations) / len(completed_job_durations) if completed_job_durations else 0
        
        total_records = ExtractionJob.objects.aggregate(
            total=Sum('record_count')
        )['total'] or 0
        
        return {
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'pending_jobs': pending_jobs,
            'in_progress_jobs': in_progress_jobs,
            'cancelled_jobs': cancelled_jobs,
            'average_duration_seconds': avg_duration,
            'total_records_extracted': total_records
        }
    
    @staticmethod
    def process_extraction_manually(job_id: str) -> bool:
        """Manually process an extraction (for testing purposes)"""
        try:
            ExtractionService._process_extraction(job_id)
            return True
        except Exception:
            return False
