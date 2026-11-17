from django.db import models


class User(models.Model):
    is_authenticated = True

    ROLE_CHOICES = (
        ('USER', 'User'),
        ('COLLECTOR', 'Collector'),
        ('ADMIN', 'Admin'),
    )

    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='USER')
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class CollectorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    id_card_number = models.CharField(max_length=50, unique=True)
    assigned_district = models.CharField(max_length=50, default='Kozhikode')
    assigned_municipality = models.CharField(max_length=100, default='Kozhikode Corporation')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.user.name} - {self.assigned_municipality} (Verified: {self.is_verified})"