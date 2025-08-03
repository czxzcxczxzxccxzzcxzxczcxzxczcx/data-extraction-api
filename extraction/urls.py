from django.urls import path
from .views import (
    # New API endpoints
    ScanStartView, ScanStatusView, ScanResultView, ScanCancelView, ScanRemoveView,
    JobsListView, JobsStatisticsView, HealthCheckView,
    # Legacy endpoint
    ExtractionJobList
)

urlpatterns = [
    # Scan endpoints
    path('scan/start/', ScanStartView.as_view(), name='scan-start'),
    path('scan/status/<uuid:job_id>/', ScanStatusView.as_view(), name='scan-status'),
    path('scan/result/<uuid:job_id>/', ScanResultView.as_view(), name='scan-result'),
    path('scan/cancel/<uuid:job_id>/', ScanCancelView.as_view(), name='scan-cancel'),
    path('scan/remove/<uuid:job_id>/', ScanRemoveView.as_view(), name='scan-remove'),
    
    # Jobs endpoints
    path('jobs/jobs/', JobsListView.as_view(), name='jobs-list'),
    path('jobs/statistics/', JobsStatisticsView.as_view(), name='jobs-statistics'),
    
    # Health check
    path('health/', HealthCheckView.as_view(), name='health-check'),

    # Legacy endpoint for backwards compatibility
    path('jobs/', ExtractionJobList.as_view(), name='job-list'),
]
