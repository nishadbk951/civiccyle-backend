from django.urls import path
from .views import (
    WasteRequestCreateView,
    UserWasteRequestListView,
    CollectorAssignedWasteListView,
    AcceptPickupView,
    RejectPickupView,
    CompletePickupView,
    UpdateWasteStatusView,
    AdminAllWasteRequestsView,
    AdminReopenRequestView,
    AdminAnalyticsOverviewView,
)

urlpatterns = [
    
    path('request/', WasteRequestCreateView.as_view(), name='waste-request-create'),
    path('my-requests/', UserWasteRequestListView.as_view(), name='my-waste-requests'),
    path('collector/assigned/', CollectorAssignedWasteListView.as_view(), name='collector-assigned-requests'),
    path('collector/accept/<int:pk>/', AcceptPickupView.as_view(), name='collector-accept-request'),
    path('collector/reject/<int:pk>/', RejectPickupView.as_view(), name='collector-reject-request'),
    path('collector/complete/<int:pk>/', CompletePickupView.as_view(), name='collector-complete-request'),
    path('collector/update/<int:pk>/', UpdateWasteStatusView.as_view(), name='update-waste-status'),

    
    path('admin/all-requests/', AdminAllWasteRequestsView.as_view(), name='admin-all-requests'),
    path('admin/reopen/<int:pk>/', AdminReopenRequestView.as_view(), name='admin-reopen-request'),
    path('admin/analytics/', AdminAnalyticsOverviewView.as_view(), name='admin-analytics'),
]