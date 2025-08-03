from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import ExtractionJob, ExtractedRecord
from .serializers import (
    ExtractionJobSerializer, JobStartSerializer, JobStatusSerializer,
    JobStatisticsSerializer, HealthSerializer, ExtractedRecordSerializer
)
from .services import ExtractionService


class ScanStartView(APIView):
    """Start a new data extraction job"""
    
    @extend_schema(
        summary="Start Data Extraction",
        description="Initiate a new data extraction job from a third-party service using an API token.",
        request=JobStartSerializer,
        responses={
            202: OpenApiExample(
                'Success',
                value={
                    'job_id': '123e4567-e89b-12d3-a456-426614174000',
                    'status': 'pending',
                    'message': 'Extraction job started successfully'
                }
            ),
            400: OpenApiExample('Bad Request', value={'error': 'Invalid API token'}),
            500: OpenApiExample('Server Error', value={'error': 'Failed to start extraction'})
        },
        tags=['Data Extraction']
    )
    def post(self, request):
        serializer = JobStartSerializer(data=request.data)
        if serializer.is_valid():
            api_token = serializer.validated_data['api_token']
            
            try:
                job = ExtractionService.start_extraction(api_token)
                response_data = {
                    'job_id': str(job.job_id),
                    'status': job.status,
                    'message': 'Extraction job started successfully'
                }
                return Response(response_data, status=status.HTTP_202_ACCEPTED)
            except Exception as e:
                return Response(
                    {'error': f'Failed to start extraction: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScanStatusView(APIView):
    """Get the status of a specific extraction job"""
    
    @extend_schema(
        summary="Get Job Status",
        description="Retrieve the current status and progress of a specific extraction job.",
        responses={
            200: JobStatusSerializer,
            404: OpenApiExample('Not Found', value={'error': 'Job not found'})
        },
        tags=['Data Extraction']
    )
    def get(self, request, job_id):
        try:
            job = ExtractionJob.objects.get(job_id=job_id)
            serializer = JobStatusSerializer(job)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ExtractionJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class ScanResultView(APIView):
    """Get the results of a completed extraction job"""
    
    @extend_schema(
        summary="Get Extraction Results",
        description="Retrieve the extracted data for a completed job. Supports pagination for large datasets.",
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination (default: 1)'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of records per page (default: 20)'
            )
        ],
        responses={
            200: OpenApiExample(
                'Success',
                value={
                    'job_id': '123e4567-e89b-12d3-a456-426614174000',
                    'status': 'completed',
                    'total_records': 25,
                    'page': 1,
                    'page_size': 20,
                    'total_pages': 2,
                    'has_next': True,
                    'has_previous': False,
                    'results': [
                        {
                            'id_from_service': 'user_1',
                            'email': 'user1@example.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'additional_data': {'phone': '+1-555-1234'}
                        }
                    ]
                }
            ),
            404: OpenApiExample('Not Found', value={'error': 'Job not found'}),
            409: OpenApiExample('Conflict', value={'error': 'Job is not completed. Current status: pending'})
        },
        tags=['Data Extraction']
    )
    def get(self, request, job_id):
        try:
            job = ExtractionJob.objects.get(job_id=job_id)
            
            if job.status != 'completed':
                return Response(
                    {'error': f'Job is not completed. Current status: {job.status}'}, 
                    status=status.HTTP_409_CONFLICT
                )
            
            # Get pagination parameters with error handling
            try:
                page = int(request.GET.get('page', 1))
                page_size = int(request.GET.get('page_size', 20))
            except ValueError:
                return Response(
                    {'error': 'Invalid pagination parameters'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get records for this job
            records = job.records.all()
            paginator = Paginator(records, page_size)
            
            try:
                page_obj = paginator.get_page(page)
            except:
                return Response(
                    {'error': 'Invalid page number'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = ExtractedRecordSerializer(page_obj, many=True)
            
            response_data = {
                'job_id': str(job.job_id),
                'status': job.status,
                'total_records': job.record_count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'results': serializer.data
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ExtractionJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class ScanCancelView(APIView):
    """Cancel a pending or in-progress extraction job"""
    
    @extend_schema(
        summary="Cancel Job",
        description="Cancel a pending or in-progress extraction job. Completed, failed, or already cancelled jobs cannot be cancelled.",
        responses={
            200: OpenApiExample('Success', value={'message': 'Job cancelled successfully', 'job_id': '123e4567-e89b-12d3-a456-426614174000'}),
            404: OpenApiExample('Not Found', value={'error': 'Job not found'}),
            409: OpenApiExample('Conflict', value={'error': 'Job cannot be cancelled. Current status: completed'})
        },
        tags=['Data Extraction']
    )
    def post(self, request, job_id):
        try:
            job = ExtractionJob.objects.get(job_id=job_id)
            
            if not job.can_be_cancelled():
                return Response(
                    {'error': f'Job cannot be cancelled. Current status: {job.status}'}, 
                    status=status.HTTP_409_CONFLICT
                )
            
            success = ExtractionService.cancel_job(job_id)
            if success:
                return Response(
                    {'message': 'Job cancelled successfully', 'job_id': str(job_id)}, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'Failed to cancel job'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except ExtractionJob.DoesNotExist:
            return Response(
                {'error': 'Job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class ScanRemoveView(APIView):
    """Remove all data associated with an extraction job"""
    
    @extend_schema(
        summary="Remove Job Data",
        description="Delete all stored extraction data associated with a specific job. This action is irreversible.",
        responses={
            200: OpenApiExample('Success', value={'message': 'Job data removed successfully'}),
            404: OpenApiExample('Not Found', value={'error': 'Job not found'})
        },
        tags=['Data Extraction']
    )
    def delete(self, request, job_id):
        success = ExtractionService.remove_job_data(job_id)
        if success:
            return Response(
                {'message': 'Job data removed successfully'}, 
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'error': 'Job not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class JobsListView(APIView):
    """List all extraction jobs with pagination and filtering"""
    
    @extend_schema(
        summary="List All Jobs",
        description="Retrieve a list of all extraction jobs with optional status filtering and pagination support.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter jobs by status (pending, in_progress, completed, failed, cancelled)'
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination (default: 1)'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of jobs per page (default: 20)'
            )
        ],
        responses={
            200: OpenApiExample(
                'Success',
                value={
                    'page': 1,
                    'page_size': 20,
                    'total_pages': 3,
                    'total_jobs': 50,
                    'has_next': True,
                    'has_previous': False,
                    'results': [
                        {
                            'job_id': '123e4567-e89b-12d3-a456-426614174000',
                            'status': 'completed',
                            'record_count': 25,
                            'created_at': '2023-01-01T10:00:00Z'
                        }
                    ]
                }
            )
        },
        tags=['Job Management']
    )
    def get(self, request):
        # Get filter parameters
        status_filter = request.GET.get('status')
        
        # Get pagination parameters with error handling
        try:
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
        except ValueError:
            return Response(
                {'error': 'Invalid pagination parameters'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build queryset
        queryset = ExtractionJob.objects.all()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Paginate
        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.get_page(page)
        except:
            return Response(
                {'error': 'Invalid page number'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ExtractionJobSerializer(page_obj, many=True)
        
        response_data = {
            'page': page,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_jobs': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'results': serializer.data
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class JobsStatisticsView(APIView):
    """Get overall statistics about extraction jobs"""
    
    @extend_schema(
        summary="Get Job Statistics",
        description="Retrieve aggregated statistics about all extraction jobs including counts by status, average duration, and total records extracted.",
        responses={200: JobStatisticsSerializer},
        tags=['Job Management']
    )
    def get(self, request):
        stats = ExtractionService.get_job_statistics()
        serializer = JobStatisticsSerializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)


class HealthCheckView(APIView):
    """Health check endpoint"""
    
    @extend_schema(
        summary="Health Check",
        description="Check the operational status and health of the API service.",
        responses={200: HealthSerializer},
        tags=['System']
    )
    def get(self, request):
        health_data = {
            'status': 'ok',
            'timestamp': timezone.now(),
            'version': '1.0.0'
        }
        serializer = HealthSerializer(health_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Legacy view for backwards compatibility
class ExtractionJobList(APIView):
    def get(self, request):
        jobs = ExtractionJob.objects.all()
        serializer = ExtractionJobSerializer(jobs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ExtractionJobSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
