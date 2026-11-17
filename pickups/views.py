import random
from collections import defaultdict
from django.db.models import Q, Count
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from accounts.models import User, CollectorProfile
from .models import WasteRequest
from .serializers import WasteRequestSerializer
from .ai_service import analyze_waste_image



def normalize_waste_category(raw_name):
    if not raw_name:
        return "OTHER"
    text = str(raw_name).strip().upper()

    if text in ["PLASTIC", "METAL", "PAPER", "E_WASTE", "FURNITURE", "GLASS", "TEXTILE"]:
        return text
    if "PLASTIC" in text or "BOTTLE" in text:
        return "PLASTIC"
    if "CLOTH" in text or "TEXTILE" in text or "FABRIC" in text:
        return "TEXTILE"
    if "E-WASTE" in text or "EWASTE" in text or "ELECTRONIC" in text or "CABLE" in text:
        return "E_WASTE"
    if "METAL" in text or "IRON" in text or "STEEL" in text or "ALUMINIUM" in text:
        return "METAL"
    if "PAPER" in text or "CARDBOARD" in text or "BOOK" in text:
        return "PAPER"
    if "WOOD" in text or "FURNITURE" in text or "SOFA" in text or "CHAIR" in text:
        return "FURNITURE"
    if "GLASS" in text:
        return "GLASS"
    return text


class WasteRequestCreateView(generics.CreateAPIView):
    queryset = WasteRequest.objects.all()
    serializer_class = WasteRequestSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_image = request.FILES.get('image')
        if not uploaded_image:
            return Response(
                {"error": "Please upload an image of the waste."},
                status=status.HTTP_400_BAD_REQUEST
            )

        ai_result = analyze_waste_image(uploaded_image)

        if not ai_result.get("is_valid", False):
            return Response(
                {"error": ai_result.get("error_message", "Invalid waste image.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        detected_item = normalize_waste_category(ai_result.get("detected_item", "PLASTIC"))
        serializer.save(user=request.user, ai_detected_item=detected_item)

        return Response(
            {
                "message": "Pickup request submitted successfully!",
                "data": serializer.data
            },
            status=status.HTTP_201_CREATED
        )

class UserWasteRequestListView(generics.ListAPIView):
    serializer_class = WasteRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            WasteRequest.objects.select_related('user', 'assigned_collector')
            .filter(user=self.request.user)
            .order_by('-created_at')
        )


class CollectorAssignedWasteListView(generics.ListAPIView):
    serializer_class = WasteRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'collectorprofile', None) or getattr(user, 'collector_profile', None)

        if profile and profile.is_verified:
            collector_muni = profile.assigned_municipality
            return (
                WasteRequest.objects.select_related('user', 'assigned_collector')
                .filter(
                    Q(municipality=collector_muni, status='PENDING') |
                    Q(assigned_collector=user, status__in=['IN_PROGRESS', 'COMPLETED', 'REJECTED'])
                )
                .order_by('-created_at')
            )
        return WasteRequest.objects.none()


class AcceptPickupView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            waste_request = WasteRequest.objects.get(id=pk, status='PENDING')
        except WasteRequest.DoesNotExist:
            return Response(
                {"error": "This request is no longer available or has already been accepted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        remark = request.data.get('collector_remark', 'Accepted — Scheduled for doorstep pickup today.')
        generated_otp = str(random.randint(1000, 9999))

        waste_request.status = 'IN_PROGRESS'
        waste_request.assigned_collector = request.user
        waste_request.collector_remark = remark
        waste_request.pickup_otp = generated_otp
        waste_request.save(update_fields=['status', 'assigned_collector', 'collector_remark', 'pickup_otp'])

        return Response(
            {
                "message": "Pickup request accepted! A 4-digit Pickup PIN has been sent to the citizen.",
                "status": "IN_PROGRESS",
                "collector_remark": remark,
                "pickup_otp": generated_otp
            },
            status=status.HTTP_200_OK
        )


class RejectPickupView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            waste_request = WasteRequest.objects.get(id=pk, status='PENDING')
        except WasteRequest.DoesNotExist:
            return Response(
                {"error": "This request is no longer available."},
                status=status.HTTP_400_BAD_REQUEST
            )

        remark = request.data.get('collector_remark', 'Quantity too low or item cannot be collected.')

        waste_request.status = 'REJECTED'
        waste_request.assigned_collector = request.user
        waste_request.collector_remark = remark
        waste_request.save(update_fields=['status', 'assigned_collector', 'collector_remark'])

        return Response(
            {
                "message": "Pickup request rejected.",
                "status": "REJECTED",
                "collector_remark": remark
            },
            status=status.HTTP_200_OK
        )



class CompletePickupView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            waste_request = WasteRequest.objects.get(
                id=pk,
                assigned_collector=request.user,
                status='IN_PROGRESS'
            )
        except WasteRequest.DoesNotExist:
            return Response(
                {"error": "Pickup request not found or not assigned to you in progress."},
                status=status.HTTP_400_BAD_REQUEST
            )

        entered_otp = str(request.data.get('otp', '')).strip()

        if not entered_otp:
            return Response(
                {"error": "Please enter the 4-digit Pickup PIN provided by the citizen."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if waste_request.pickup_otp != entered_otp:
            return Response(
                {"error": "Invalid Pickup PIN! Please ask the citizen for the correct 4-digit code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        waste_request.status = 'COMPLETED'
        waste_request.pickup_otp = None
        waste_request.save(update_fields=['status', 'pickup_otp'])

        return Response(
            {
                "message": "PIN verified! Pickup marked as completed successfully.",
                "status": "COMPLETED"
            },
            status=status.HTTP_200_OK
        )


class UpdateWasteStatusView(generics.UpdateAPIView):
    serializer_class = WasteRequestSerializer
    permission_classes = [IsAuthenticated]
    queryset = WasteRequest.objects.all()

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        new_status = request.data.get('status')

        if new_status == 'CANCELLED' and instance.user == request.user and instance.status == 'PENDING':
            instance.status = 'CANCELLED'
            instance.save(update_fields=['status'])
            return Response(
                {"message": "Waste request cancelled successfully!"},
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "Only pending requests can be cancelled by the owner."},
            status=status.HTTP_400_BAD_REQUEST
        )



class AdminAllWasteRequestsView(generics.ListAPIView):
    serializer_class = WasteRequestSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return WasteRequest.objects.select_related('user', 'assigned_collector').all().order_by('-created_at')



class AdminReopenRequestView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            waste_request = WasteRequest.objects.get(id=pk)
        except WasteRequest.DoesNotExist:
            return Response({"error": "Waste request not found."}, status=status.HTTP_404_NOT_FOUND)

        if waste_request.status != 'IN_PROGRESS':
            return Response(
                {"error": "Only IN_PROGRESS requests can be re-opened."},
                status=status.HTTP_400_BAD_REQUEST
            )

        waste_request.status = 'PENDING'
        waste_request.assigned_collector = None
        waste_request.pickup_otp = None
        waste_request.collector_remark = "Re-opened by Admin for reassignment."
        waste_request.save(update_fields=['status', 'assigned_collector', 'pickup_otp', 'collector_remark'])

        return Response(
            {"message": f"Request #{waste_request.id} has been re-opened to PENDING."},
            status=status.HTTP_200_OK
        )



class AdminAnalyticsOverviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        
        citizens_qs = (
            User.objects.filter(role='USER')
            .annotate(total_requests=Count('waste_requests'))
            .order_by('-created_at')
        )
        total_citizens = citizens_qs.count()

        citizens_list = [
            {
                "id": u.id,
                "name": u.name or 'Citizen',
                "phone": u.phone or 'N/A',
                "joined_at": u.created_at.strftime('%d %b %Y, %I:%M %p') if getattr(u, 'created_at', None) else 'N/A',
                "is_active": getattr(u, 'is_active', True),
                "total_requests": u.total_requests,
            }
            for u in citizens_qs
        ]

        total_collectors = CollectorProfile.objects.count()
        pending_collector_approvals = CollectorProfile.objects.filter(is_verified=False).count()

        total_requests = WasteRequest.objects.count()
        pending_requests = WasteRequest.objects.filter(status='PENDING').count()
        in_progress_requests = WasteRequest.objects.filter(status='IN_PROGRESS').count()
        completed_requests = WasteRequest.objects.filter(status='COMPLETED').count()
        rejected_requests = WasteRequest.objects.filter(status='REJECTED').count()

        raw_items = (
            WasteRequest.objects.exclude(ai_detected_item__isnull=True)
            .exclude(ai_detected_item__exact='')
            .values_list('ai_detected_item', flat=True)
        )

        grouped_counts = defaultdict(int)
        for item in raw_items:
            clean_cat = normalize_waste_category(item)
            grouped_counts[clean_cat] += 1

        categorized_total = sum(grouped_counts.values())
        waste_categories = []
        for cat_name, count in sorted(grouped_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((count / categorized_total) * 100, 1) if categorized_total > 0 else 0
            waste_categories.append({
                "ai_detected_item": cat_name,
                "count": count,
                "percentage": pct,
            })

        district_qs = (
            WasteRequest.objects.exclude(district__isnull=True)
            .exclude(district__exact='')
            .values('district')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        district_breakdown = [
            {
                "district": d['district'],
                "count": d['count'],
                "percentage": round((d['count'] / total_requests) * 100, 1) if total_requests > 0 else 0,
            }
            for d in district_qs
        ]

        municipality_qs = (
            WasteRequest.objects.values('district', 'municipality')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        municipality_breakdown = [
            {
                "district": m['district'],
                "municipality": m['municipality'],
                "count": m['count'],
                "percentage": round((m['count'] / total_requests) * 100, 1) if total_requests > 0 else 0,
            }
            for m in municipality_qs
        ]

        return Response({
            "kpis": {
                "total_citizens": total_citizens,
                "total_collectors": total_collectors,
                "pending_collector_approvals": pending_collector_approvals,
                "total_requests": total_requests,
                "pending_requests": pending_requests,
                "in_progress_requests": in_progress_requests,
                "completed_requests": completed_requests,
                "rejected_requests": rejected_requests,
            },
            "waste_categories": waste_categories,
            "district_breakdown": district_breakdown,
            "municipality_breakdown": municipality_breakdown,
            "citizens_list": citizens_list,
        }, status=status.HTTP_200_OK)