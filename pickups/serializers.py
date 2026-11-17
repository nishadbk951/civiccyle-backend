from rest_framework import serializers
from .models import WasteRequest

LOCATION_MAPPING = {
    "Kozhikode": [
        "Kozhikode Corporation",
        "Vadakara Municipality",
        "Feroke Municipality",
        "Ramanattukara Municipality"
    ],
    "Malappuram": [
        "Manjeri Municipality",
        "Malappuram Municipality",
        "Tirur Municipality",
        "Perinthalmanna Municipality"
    ],
    "Palakkad": [
        "Palakkad Municipality",
        "Ottapalam Municipality",
        "Shornur Municipality",
        "Chittur Municipality"
    ]
}


class WasteRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.name')
    user_phone = serializers.ReadOnlyField(source='user.phone')
    collector_name = serializers.ReadOnlyField(source='assigned_collector.name')

    class Meta:
        model = WasteRequest
        fields = [
            'id',
            'user',
            'user_name',
            'user_phone',
            'assigned_collector',
            'collector_name',
            'waste_type',
            'image',
            'ai_detected_item',
            'collector_remark',
            'pickup_otp',
            'district',
            'municipality',
            'ward_no',
            'house_details',
            'latitude',
            'longitude',
            'status',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'user',
            'assigned_collector',
            'ai_detected_item',
            'collector_remark',
            'pickup_otp',
            'status',
            'created_at'
        ]

    def to_representation(self, instance):
        
        data = super().to_representation(instance)
        request = self.context.get('request')

        if request and request.user != instance.user:
            data.pop('pickup_otp', None)

        return data

    def validate(self, data):
        district = data.get('district')
        municipality = data.get('municipality')

        if district is not None:
            if district not in LOCATION_MAPPING:
                raise serializers.ValidationError({
                    "district": f"Invalid district '{district}'. Supported districts are {list(LOCATION_MAPPING.keys())}."
                })

            valid_municipalities = LOCATION_MAPPING[district]
            if municipality not in valid_municipalities:
                raise serializers.ValidationError({
                    "municipality": f"'{municipality}' does not belong to {district}. Valid options: {valid_municipalities}."
                })

        return data