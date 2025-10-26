from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.contrib.auth import get_user_model

# Create your models here.
class User(AbstractUser):
    ROLE_CHOICES = (
        ("customer", "Customer"),
        ("admin", "Admin"),
        ("auditor", "Auditor"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    full_name = models.CharField(max_length=255)
    kyc_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class KYC(models.Model):
    DOCUMENT_TYPES = (
        ("pan", "PAN Card"),
        ("aadhar", "Aadhar Card"),
        ("passport", "Passport"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="kyc")
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to="kyc/")
    status = models.CharField(max_length=20, default="pending")
    notes = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"KYC({self.user.username} - {self.status})"


class BankAccount(models.Model):
    ACCOUNT_TYPES = (
        ("savings", "Savings"),
        ("current", "Current"),
        ("fd", "Fixed Deposit"),
    )

    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name="accounts")
    account_number = models.CharField(max_length=12, unique=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account_type.upper()} - {self.account_number}"

    @staticmethod
    def generate_account_number():
        # Generate numeric account number from UUID (max 12 digits)
        return str(uuid.uuid4().int)[:12]


class Transaction(models.Model):
    STATUS_CHOICES = (
        ("success", "Success"),
        ("failed", "Failed"),
    )

    transaction_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    from_account = models.ForeignKey(
        BankAccount,
        related_name="outgoing_transfers",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    to_account = models.ForeignKey(
        BankAccount,
        related_name="incoming_transfers",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-timestamp"]

    def __str__(self):
        username = self.user.username if self.user else "Anonymous"
        return f"{username} - {self.action} - - {self.ip_address} - {self.timestamp}"
