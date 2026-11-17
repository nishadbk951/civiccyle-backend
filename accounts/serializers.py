from rest_framework import serializers
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, CollectorProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    assigned_district = serializers.CharField(write_only=True, required=False, allow_blank=True)
    assigned_municipality = serializers.CharField(write_only=True, required=False, allow_blank=True)
    id_card_number = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'phone', 'password', 'role', 'assigned_district', 'assigned_municipality', 'id_card_number']

    def create(self, validated_data):
        
        district = validated_data.pop('assigned_district', '')
        municipality = validated_data.pop('assigned_municipality', '')
        id_card = validated_data.pop('id_card_number', '')

        
        validated_data['password'] = make_password(validated_data['password'])
        user = super().create(validated_data)

        
        if user.role == 'COLLECTOR':
            CollectorProfile.objects.create(
                user=user,
                assigned_district=district or 'Kozhikode',
                assigned_municipality=municipality or 'Kozhikode Corporation',
                id_card_number=id_card or 'TEMP_ID',
                is_verified=False  
            )

        return user


class UserLoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone = data.get('phone')
        password = data.get('password')

        
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            
            raise serializers.ValidationError({"error": "Invalid phone number or password."})

        
        if not check_password(password, user.password):
            raise serializers.ValidationError({"error": "Invalid phone number or password."})

        
        if user.role == 'COLLECTOR':
            try:
                collector_profile = user.collectorprofile
            except Exception:
                raise serializers.ValidationError({"error": "Collector profile details not found."})
            
            if not collector_profile.is_verified:
                raise serializers.ValidationError({"error": "Your collector profile is pending admin verification."})

        
        refresh = RefreshToken.for_user(user)

        return {
            'message': 'Login Successful.',
            'user_id': user.id,
            'name': user.name,
            'role': user.role,
            'access': str(refresh.access_token),   
            'refresh': str(refresh),               
            'access_token': str(refresh.access_token)
        }