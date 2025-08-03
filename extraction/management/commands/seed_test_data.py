from django.core.management.base import BaseCommand
from django.utils import timezone
from extraction.models import ExtractionJob, ExtractedRecord
import uuid
import random


class Command(BaseCommand):
    help = 'Seed the database with test extraction jobs and records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            ExtractedRecord.objects.all().delete()
            ExtractionJob.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared existing data'))

        self.stdout.write('Seeding test data...')

        # Create test jobs with different statuses
        jobs_data = [
            {
                'status': 'completed',
                'api_token': 'test_token_completed_001',
                'record_count': 15,
                'start_time': timezone.now() - timezone.timedelta(hours=2),
                'end_time': timezone.now() - timezone.timedelta(hours=1, minutes=30),
            },
            {
                'status': 'completed',
                'api_token': 'test_token_completed_002',
                'record_count': 8,
                'start_time': timezone.now() - timezone.timedelta(hours=5),
                'end_time': timezone.now() - timezone.timedelta(hours=4, minutes=45),
            },
            {
                'status': 'pending',
                'api_token': 'test_token_pending_001',
                'record_count': 0,
            },
            {
                'status': 'in_progress',
                'api_token': 'test_token_in_progress_001',
                'record_count': 0,
                'start_time': timezone.now() - timezone.timedelta(minutes=30),
            },
            {
                'status': 'failed',
                'api_token': 'invalid_token_fail',
                'record_count': 0,
                'error_message': 'Invalid API token provided',
                'start_time': timezone.now() - timezone.timedelta(hours=1),
                'end_time': timezone.now() - timezone.timedelta(minutes=55),
            },
            {
                'status': 'cancelled',
                'api_token': 'test_token_cancelled_001',
                'record_count': 0,
                'start_time': timezone.now() - timezone.timedelta(hours=3),
                'end_time': timezone.now() - timezone.timedelta(hours=2, minutes=45),
            },
        ]

        created_jobs = []
        for job_data in jobs_data:
            job = ExtractionJob.objects.create(**job_data)
            created_jobs.append(job)
            self.stdout.write(f'Created job {job.job_id} with status {job.status}')

        # Create extracted records for completed jobs
        for job in created_jobs:
            if job.status == 'completed':
                self.create_records_for_job(job, job.record_count)

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(created_jobs)} jobs'))

    def create_records_for_job(self, job, count):
        """Create mock extracted records for a job"""
        records = []
        for i in range(1, count + 1):
            record = ExtractedRecord(
                job=job,
                id_from_service=f'seed_user_{job.job_id}_{i}',
                email=f'seeduser{i}@example.com',
                first_name=f'SeedFirst{i}',
                last_name=f'SeedLast{i}',
                additional_data={
                    'phone': f'+1-555-{random.randint(1000, 9999)}',
                    'company': f'Seed Company {i}',
                    'department': random.choice(['Engineering', 'Sales', 'Marketing', 'HR']),
                    'created_date': '2023-01-01'
                }
            )
            records.append(record)

        ExtractedRecord.objects.bulk_create(records)
        self.stdout.write(f'Created {count} records for job {job.job_id}')
