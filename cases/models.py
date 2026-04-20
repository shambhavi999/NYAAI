"""
NYAAI - cases/models.py
The core of the platform — every legal case a user creates
"""

from django.db import models
from django.contrib.auth.models import User


class Case(models.Model):

    STATUS_CHOICES = [
        ('draft',    'Draft'),
        ('active',   'Active'),
        ('notice_sent', 'Notice Sent'),
        ('resolved', 'Resolved'),
        ('closed',   'Closed'),
    ]

    CATEGORY_CHOICES = [
        ('landlord',   'Landlord Dispute'),
        ('shopping',   'Online Shopping Fraud'),
        ('salary',     'Salary & PF Issue'),
        ('bank',       'Bank & Finance'),
        ('medical',    'Medical Negligence'),
        ('telecom',    'Telecom Dispute'),
        ('service',    'Service Fraud'),
        ('product',    'Product Defect'),
        ('other',      'Other'),
    ]

    # Owner
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cases'
    )

    # Case details
    title       = models.CharField(max_length=200)
    description = models.TextField()
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    language    = models.CharField(max_length=5, default='en')

    # AI results
    laws_violated    = models.JSONField(null=True, blank=True)
    forum_type       = models.CharField(max_length=200, blank=True)
    forum_address    = models.TextField(blank=True)
    documents_needed = models.JSONField(null=True, blank=True)
    ai_summary       = models.TextField(blank=True)
    confidence_score = models.FloatField(null=True, blank=True)

    # Status
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    notice_sent = models.BooleanField(default=False)
    is_analysed = models.BooleanField(default=False)

    # Timestamps
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Case'

    def __str__(self):
        return f"{self.user.username} — {self.title[:50]}"


class LegalNotice(models.Model):
    """Generated legal notice for a case."""

    case         = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='notices')
    notice_text  = models.TextField()
    pdf_file     = models.FileField(upload_to='notices/', null=True, blank=True)
    version      = models.IntegerField(default=1)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']

    def __str__(self):
        return f"Notice v{self.version} — {self.case.title[:40]}"


class CaseTimeline(models.Model):
    """Next steps and deadlines for a case."""

    case        = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='timeline')
    step        = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    due_date    = models.DateField(null=True, blank=True)
    completed   = models.BooleanField(default=False)
    order       = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.case.title[:30]} — {self.step[:40]}"
