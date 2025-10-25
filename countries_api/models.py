from django.db import models
from django.utils import timezone


class Country(models.Model):
    """
    Model to store country information with currency and exchange rate data
    """
    name = models.CharField(max_length=255, unique=True, db_index=True)
    capital = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    population = models.BigIntegerField()
    currency_code = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    exchange_rate = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        null=True,
        blank=True
    )
    estimated_gdp = models.DecimalField(
        max_digits=30,
        decimal_places=2,
        null=True,
        blank=True
    )
    flag_url = models.URLField(max_length=500, null=True, blank=True)
    last_refreshed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'countries'
        ordering = ['-last_refreshed_at']
        verbose_name = 'Country'
        verbose_name_plural = 'Countries'

    def __str__(self):
        return self.name


class RefreshMetadata(models.Model):
    """
    Model to store metadata about the last refresh operation
    """
    total_countries = models.IntegerField(default=0)
    last_refreshed_at = models.DateTimeField(default=timezone.now)
    refresh_status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('in_progress', 'In Progress')
        ],
        default='success'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'refresh_metadata'
        ordering = ['-last_refreshed_at']
        verbose_name = 'Refresh Metadata'
        verbose_name_plural = 'Refresh Metadata'
        get_latest_by = 'last_refreshed_at'

    def __str__(self):
        return f"Refresh at {self.last_refreshed_at} - {self.total_countries} countries"
