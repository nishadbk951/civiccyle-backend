from django.contrib import admin
from .models import User, CollectorProfile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'role')
    list_filter = ('role',)
    search_fields = ('name', 'phone')


@admin.register(CollectorProfile)
class CollectorProfileAdmin(admin.ModelAdmin):
    
    list_display = (
        'id',
        'user',
        'assigned_district',
        'assigned_municipality',
        'id_card_number',
        'is_verified'
    )
    
    
    list_editable = (
        'is_verified',
    )
    
    
    list_filter = (
        'is_verified',
        'assigned_district',
        'assigned_municipality'
    )
    
    
    search_fields = (
        'user__name',
        'user__phone',
        'id_card_number',
        'assigned_municipality'
    )
