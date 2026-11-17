from django.contrib import admin
from .models import WasteRequest

@admin.register(WasteRequest)
class WasteRequestAdmin(admin.ModelAdmin):
    
    list_display = (
        'id', 
        'user', 
        'waste_type', 
        'district', 
        'municipality', 
        'ward_no', 
        'status', 
        'created_at'
    )

    
    list_filter = ('status', 'waste_type', 'district', 'municipality', 'created_at')

    
    search_fields = ('user__name', 'user__phone', 'district', 'municipality', 'house_details')

    
    list_editable = ('status',)