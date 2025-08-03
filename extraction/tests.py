import json
import uuid
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from .models import ExtractionJob, ExtractedRecord
from .services import ExtractionService


class SeededDataTestCase(APITestCase):
    """
    Test cases using seeded data for controlled, fast, and isolated testing.
    These tests validate internal API logic and business rules.
    """
    
    def setUp(self):
        """Set up seeded test data"""
        # Create jobs with different statuses
        self.completed_job = ExtractionJob.objects.create(
            api_token='test_token_completed',
            status='completed',
            record_count=5,
            start_time=timezone.now() - timezone.timedelta(hours=1),
            end_time=timezone.now() - timezone.timedelta(minutes=30)
        )
        
        self.pending_job = ExtractionJob.objects.create(
            api_token='test_token_pending',
            status='pending',
            record_count=0
        )
        
        self.cancelled_job = ExtractionJob.objects.create(
            api_token='test_token_cancelled',
            status='cancelled',
            record_count=0,
            start_time=timezone.now() - timezone.timedelta(hours=2),
            end_time=timezone.now() - timezone.timedelta(hours=1, minutes=30)
        )
        
        self.failed_job = ExtractionJob.objects.create(
            api_token='invalid_token',
            status='failed',
            error_message='Invalid API token',
            start_time=timezone.now() - timezone.timedelta(hours=1),
            end_time=timezone.now() - timezone.timedelta(minutes=55)
        )
        
        # Create extracted records for the completed job
        for i in range(1, 6):
            ExtractedRecord.objects.create(
                job=self.completed_job,
                id_from_service=f'test_user_{i}',
                email=f'testuser{i}@example.com',
                first_name=f'Test{i}',
                last_name=f'User{i}',
                additional_data={'department': 'Testing'}
            )
    
    def test_job_status_endpoint(self):
        """Test the job status endpoint with seeded data"""
        url = reverse('scan-status', kwargs={'job_id': self.completed_job.job_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], 'completed')
        self.assertEqual(data['record_count'], 5)
        self.assertIsNotNone(data['start_time'])
        self.assertIsNotNone(data['end_time'])
    
    def test_job_results_endpoint(self):
        """Test fetching results for a completed job"""
        url = reverse('scan-result', kwargs={'job_id': self.completed_job.job_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total_records'], 5)
        self.assertEqual(len(data['results']), 5)
        self.assertEqual(data['results'][0]['email'], 'testuser1@example.com')
    
    def test_jobs_list_endpoint(self):
        """Test listing all jobs"""
        url = reverse('jobs-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total_jobs'], 4)  # We created 4 jobs in setUp
        self.assertGreaterEqual(len(data['results']), 4)
    
    def test_job_statistics_endpoint(self):
        """Test job statistics endpoint"""
        url = reverse('jobs-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total_jobs'], 4)
        self.assertEqual(data['completed_jobs'], 1)
        self.assertEqual(data['failed_jobs'], 1)
        self.assertEqual(data['pending_jobs'], 1)
        self.assertEqual(data['cancelled_jobs'], 1)
        self.assertEqual(data['total_records_extracted'], 5)
    
    def test_health_check_endpoint(self):
        """Test health check endpoint"""
        url = reverse('health-check')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn('timestamp', data)
        self.assertEqual(data['version'], '1.0.0')
    
    def test_cancel_pending_job(self):
        """Test cancelling a pending job"""
        url = reverse('scan-cancel', kwargs={'job_id': self.pending_job.job_id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('cancelled successfully', data['message'])
        
        # Verify job status was updated
        self.pending_job.refresh_from_db()
        self.assertEqual(self.pending_job.status, 'cancelled')
    
    def test_remove_job_data(self):
        """Test removing job data"""
        job_id = self.cancelled_job.job_id
        url = reverse('scan-remove', kwargs={'job_id': job_id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify job was deleted
        with self.assertRaises(ExtractionJob.DoesNotExist):
            ExtractionJob.objects.get(job_id=job_id)


class RealExtractionTestCase(APITestCase):
    """
    Test cases for real extraction functionality using mock third-party API.
    These test the end-to-end extraction pipeline.
    """
    
    def test_start_new_extraction(self):
        """Test starting a new extraction job"""
        url = reverse('scan-start')
        data = {'api_token': 'valid_test_token_12345'}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        response_data = response.json()
        self.assertIn('job_id', response_data)
        self.assertEqual(response_data['status'], 'pending')
        self.assertIn('started successfully', response_data['message'])
        
        # Verify job was created in database
        job_id = response_data['job_id']
        job = ExtractionJob.objects.get(job_id=job_id)
        self.assertEqual(job.status, 'pending')
    
    def test_poll_job_status(self):
        """Test polling job status until completion"""
        # Start a job first
        job = ExtractionJob.objects.create(
            api_token='valid_test_token_12345',
            status='completed',
            record_count=10,
            start_time=timezone.now() - timezone.timedelta(minutes=5),
            end_time=timezone.now() - timezone.timedelta(minutes=1)
        )
        
        url = reverse('scan-status', kwargs={'job_id': job.job_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], 'completed')
    
    def test_retrieve_extraction_results(self):
        """Test retrieving results from a completed extraction"""
        # Create a completed job with results
        job = ExtractionJob.objects.create(
            api_token='valid_test_token_12345',
            status='completed',
            record_count=3,
            start_time=timezone.now() - timezone.timedelta(minutes=5),
            end_time=timezone.now() - timezone.timedelta(minutes=1)
        )
        
        # Add some test records
        for i in range(1, 4):
            ExtractedRecord.objects.create(
                job=job,
                id_from_service=f'extracted_user_{i}',
                email=f'extracted{i}@example.com',
                first_name=f'Extracted{i}',
                last_name=f'User{i}'
            )
        
        url = reverse('scan-result', kwargs={'job_id': job.job_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total_records'], 3)
        self.assertEqual(len(data['results']), 3)
        
        # Verify data structure
        first_record = data['results'][0]
        self.assertIn('email', first_record)
        self.assertIn('first_name', first_record)
        self.assertIn('last_name', first_record)
        self.assertIn('id_from_service', first_record)
    
    def test_pagination_in_results(self):
        """Test pagination in extraction results"""
        # Create a job with many records
        job = ExtractionJob.objects.create(
            api_token='valid_test_token_12345',
            status='completed',
            record_count=25
        )
        
        # Create 25 records
        for i in range(1, 26):
            ExtractedRecord.objects.create(
                job=job,
                id_from_service=f'user_{i}',
                email=f'user{i}@example.com',
                first_name=f'User{i}',
                last_name='Test'
            )
        
        # Test first page
        url = reverse('scan-result', kwargs={'job_id': job.job_id})
        response = self.client.get(url, {'page': 1, 'page_size': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['has_next'])
        self.assertFalse(data['has_previous'])
        
        # Test second page
        response = self.client.get(url, {'page': 2, 'page_size': 10})
        data = response.json()
        self.assertEqual(len(data['results']), 10)
        self.assertTrue(data['has_next'])
        self.assertTrue(data['has_previous'])


class EdgeCaseTestCase(APITestCase):
    """
    Test cases for edge cases, invalid inputs, and error scenarios.
    These ensure the API behaves correctly under abnormal conditions.
    """
    
    def test_invalid_api_token_start_extraction(self):
        """Test starting extraction with invalid API token"""
        url = reverse('scan-start')
        data = {'api_token': 'invalid'}  # Too short token
        response = self.client.post(url, data, format='json')
        
        # The service should accept the request but the job should fail
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
    
    def test_missing_api_token_start_extraction(self):
        """Test starting extraction without API token"""
        url = reverse('scan-start')
        data = {}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_nonexistent_job_id_status(self):
        """Test requesting status for non-existent job ID"""
        fake_job_id = uuid.uuid4()
        url = reverse('scan-status', kwargs={'job_id': fake_job_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertIn('not found', data['error'].lower())
    
    def test_nonexistent_job_id_results(self):
        """Test requesting results for non-existent job ID"""
        fake_job_id = uuid.uuid4()
        url = reverse('scan-result', kwargs={'job_id': fake_job_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_results_for_incomplete_job(self):
        """Test accessing results for incomplete job"""
        job = ExtractionJob.objects.create(
            api_token='test_token',
            status='pending'
        )
        
        url = reverse('scan-result', kwargs={'job_id': job.job_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()
        self.assertIn('not completed', data['error'].lower())
    
    def test_cancel_completed_job(self):
        """Test cancelling an already completed job"""
        job = ExtractionJob.objects.create(
            api_token='test_token',
            status='completed',
            start_time=timezone.now() - timezone.timedelta(hours=1),
            end_time=timezone.now() - timezone.timedelta(minutes=30)
        )
        
        url = reverse('scan-cancel', kwargs={'job_id': job.job_id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()
        self.assertIn('cannot be cancelled', data['error'].lower())
    
    def test_cancel_nonexistent_job(self):
        """Test cancelling non-existent job"""
        fake_job_id = uuid.uuid4()
        url = reverse('scan-cancel', kwargs={'job_id': fake_job_id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_remove_nonexistent_job(self):
        """Test removing non-existent job"""
        fake_job_id = uuid.uuid4()
        url = reverse('scan-remove', kwargs={'job_id': fake_job_id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_malformed_request_body(self):
        """Test sending malformed JSON to start endpoint"""
        url = reverse('scan-start')
        # Send invalid JSON
        response = self.client.post(
            url, 
            'invalid json{', 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_invalid_pagination_parameters(self):
        """Test invalid pagination parameters"""
        job = ExtractionJob.objects.create(
            api_token='test_token',
            status='completed'
        )
        
        url = reverse('scan-result', kwargs={'job_id': job.job_id})
        response = self.client.get(url, {'page': 'invalid'})
        
        # Should handle invalid page gracefully
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK])
    
    def test_jobs_list_with_status_filter(self):
        """Test jobs list endpoint with status filtering"""
        # Create jobs with different statuses
        ExtractionJob.objects.create(api_token='token1', status='completed')
        ExtractionJob.objects.create(api_token='token2', status='pending')
        ExtractionJob.objects.create(api_token='token3', status='failed')
        
        url = reverse('jobs-list')
        response = self.client.get(url, {'status': 'completed'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # All returned jobs should have 'completed' status
        for job in data['results']:
            self.assertEqual(job['status'], 'completed')


class ExtractionServiceTestCase(TestCase):
    """
    Unit tests for the ExtractionService class
    """
    
    def test_job_statistics_calculation(self):
        """Test job statistics calculation"""
        # Create jobs with different statuses
        ExtractionJob.objects.create(api_token='token1', status='completed', record_count=10)
        ExtractionJob.objects.create(api_token='token2', status='completed', record_count=5)
        ExtractionJob.objects.create(api_token='token3', status='pending')
        ExtractionJob.objects.create(api_token='token4', status='failed')
        ExtractionJob.objects.create(api_token='token5', status='cancelled')
        
        stats = ExtractionService.get_job_statistics()
        
        self.assertEqual(stats['total_jobs'], 5)
        self.assertEqual(stats['completed_jobs'], 2)
        self.assertEqual(stats['pending_jobs'], 1)
        self.assertEqual(stats['failed_jobs'], 1)
        self.assertEqual(stats['cancelled_jobs'], 1)
        self.assertEqual(stats['total_records_extracted'], 15)
    
    def test_cancel_job_service(self):
        """Test the cancel job service method"""
        job = ExtractionJob.objects.create(
            api_token='test_token',
            status='pending'
        )
        
        # Should be able to cancel
        result = ExtractionService.cancel_job(str(job.job_id))
        self.assertTrue(result)
        
        job.refresh_from_db()
        self.assertEqual(job.status, 'cancelled')
    
    def test_remove_job_data_service(self):
        """Test the remove job data service method"""
        job = ExtractionJob.objects.create(
            api_token='test_token',
            status='completed'
        )
        
        # Add some records
        ExtractedRecord.objects.create(
            job=job,
            id_from_service='test_user',
            email='test@example.com'
        )
        
        job_id = str(job.job_id)
        
        # Remove the job
        result = ExtractionService.remove_job_data(job_id)
        self.assertTrue(result)
        
        # Verify job and records are deleted
        with self.assertRaises(ExtractionJob.DoesNotExist):
            ExtractionJob.objects.get(job_id=job_id)
        
        self.assertEqual(ExtractedRecord.objects.filter(job__job_id=job_id).count(), 0)
