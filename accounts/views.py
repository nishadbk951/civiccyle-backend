from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser
from django.contrib.auth.hashers import check_password, make_password

from .models import User, CollectorProfile
from .serializers import UserRegistrationSerializer, UserLoginSerializer


class RegisterUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "User registered successfully."},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)

        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class AdminCollectorListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        profiles = CollectorProfile.objects.select_related('user').all().order_by('-id')
        data = []
        for p in profiles:
            data.append({
                "id": p.id,
                "user_id": p.user.id,
                "name": p.user.name,
                "phone": p.user.phone,
                "id_card_number": p.id_card_number,
                "assigned_district": p.assigned_district,
                "assigned_municipality": p.assigned_municipality,
                "is_verified": p.is_verified,
                "created_at": p.created_at,
            })
        return Response(data, status=status.HTTP_200_OK)


class AdminVerifyCollectorView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            profile = CollectorProfile.objects.select_related('user').get(pk=pk)
        except CollectorProfile.DoesNotExist:
            return Response({"error": "Collector profile not found."}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action", "APPROVE").upper()

        if action == "APPROVE":
            profile.is_verified = True
            profile.save()
            return Response(
                {"message": f"Collector {profile.user.name} has been verified and approved."},
                status=status.HTTP_200_OK
            )
        elif action == "REVOKE":
            profile.is_verified = False
            profile.save()
            return Response(
                {"message": f"Verification revoked for {profile.user.name}."},
                status=status.HTTP_200_OK
            )

        return Response({"error": "Invalid action. Use APPROVE or REVOKE."}, status=status.HTTP_400_BAD_REQUEST)


class AdminChangePasswordView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        old_password = request.data.get("old_password", "")
        new_password = request.data.get("new_password", "")

        if not old_password or not new_password:
            return Response({"error": "Both old and new passwords are required."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({"error": "New password must be at least 6 characters long."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not check_password(old_password, user.password):
            return Response({"error": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        user.password = make_password(new_password)
        user.save()
        return Response({"message": "Admin password updated successfully."}, status=status.HTTP_200_OK)