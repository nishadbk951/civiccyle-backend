import os
from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.db import models
from accounts.models import User


class WasteRequest(models.Model):
    WASTE_TYPE_CHOICES = [
        ('PLASTIC', 'Plastic'),
        ('METAL', 'Metal'),
        ('PAPER', 'Paper & Cardboard'),
        ('E_WASTE', 'Electronic Waste'),
        ('FURNITURE', 'Wood & Furniture'),
        ('GLASS', 'Glass'),
        ('TEXTILE', 'Textile & Old Clothes'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="waste_requests")

    assigned_collector = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_pickups"
    )

    waste_type = models.CharField(max_length=20, choices=WASTE_TYPE_CHOICES, default='PLASTIC')
    image = models.ImageField(upload_to='waste_image/')

    
    ai_detected_item = models.CharField(max_length=255, blank=True, default='')
    collector_remark = models.TextField(blank=True, default='')

    pickup_otp = models.CharField(max_length=6, null=True, blank=True)

    district = models.CharField(max_length=50, default='Kozhikode', db_index=True)
    municipality = models.CharField(max_length=100, default='Kozhikode Corporation', db_index=True)
    ward_no = models.PositiveIntegerField(default=1, db_index=True)
    house_details = models.CharField(max_length=255, default='')

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.image and hasattr(self.image, 'file') and not getattr(self.image, '_compressed', False):
            try:
                img = Image.open(self.image)
                img = ImageOps.exif_transpose(img)  

                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')

                img.thumbnail((800, 800), Image.Resampling.LANCZOS)

                output = BytesIO()
                img.save(output, format='JPEG', quality=75, optimize=True)
                output.seek(0)

                base_name = os.path.splitext(os.path.basename(self.image.name))[0]
                self.image.save(f"{base_name}.jpg", ContentFile(output.read()), save=False)
                self.image._compressed = True
            except Exception as e:
                print(f"Image compression skipped: {e}")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.name} - {self.waste_type} ({self.status})"