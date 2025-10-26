from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from users.models import User, KYC, BankAccount, Transaction, AuditLog
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

# Atomic transaction to ensure both accounts are updated safely
from django.db import transaction as db_transaction

DAILY_LIMIT = Decimal("5000.00")


class KYCReSubmitSerializer(serializers.Serializer):
    kyc_id = serializers.IntegerField()
    file = serializers.FileField()

    def validate(self, data):
        try:
            kyc = KYC.objects.get(id=data["kyc_id"], status="rejected")
        except KYC.DoesNotExist:
            raise serializers.ValidationError(
                "KYC not found or not eligible for re-submission."
            )
        data["kyc_instance"] = kyc
        return data

    def update(self, instance, validated_data):
        instance.file = validated_data["file"]
        instance.status = "pending"
        instance.notes = ""
        instance.save()
        return instance


class KYCVerifySerializer(serializers.Serializer):
    kyc_id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["verified", "rejected"])
    notes = serializers.CharField(required=False, allow_blank=True)


class KYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = ["id", "document_type", "file", "status", "submitted_at"]


class PendingKYCSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username")
    full_name = serializers.CharField(source="user.full_name")
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = KYC
        fields = [
            "id",
            "user_id",
            "username",
            "full_name",
            "document_type",
            "file_url",
            "status",
            "submitted_at",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class UserRegisterSerializer(serializers.ModelSerializer):
    document_type = serializers.ChoiceField(choices=KYC.DOCUMENT_TYPES, write_only=True)
    file = serializers.FileField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "full_name", "document_type", "file"]

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)  # Uses Django's built-in validators
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def create(self, validated_data):
        document_type = validated_data.pop("document_type")
        file = validated_data.pop("file")
        password = validated_data.pop("password")
        user = User.objects.create(
            password=make_password(password), role="customer", **validated_data
        )
        KYC.objects.create(user=user, document_type=document_type, file=file)
        return user

    def to_representation(self, instance):
        kyc = instance.kyc.first()
        return {
            "user": {
                "id": instance.id,
                "username": instance.username,
                "email": instance.email,
                "role": instance.role,
                "kyc_verified": instance.kyc_verified,
            },
            "kyc": {
                "document_type": kyc.document_type,
                "status": kyc.status,
            },
            "message": "User registered successfully. KYC pending verification.",
        }


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user registered with this email.")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def save(self):
        email = self.validated_data["email"]
        new_password = self.validated_data["new_password"]

        user = User.objects.get(email=email)
        user.password = make_password(new_password)
        user.save()
        return user


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["account_number", "account_type", "balance"]


class BankAccountCreateSerializer(serializers.ModelSerializer):
    initial_deposit = serializers.DecimalField(
        max_digits=15, decimal_places=2, write_only=True
    )

    class Meta:
        model = BankAccount
        fields = ["account_type", "initial_deposit", "account_number", "balance"]
        read_only_fields = ["account_number", "balance"]

    def validate(self, data):
        user = self.context["request"].user
        if not user.kyc_verified:
            raise serializers.ValidationError(
                "User KYC is not verified. Cannot create account."
            )
        return data

    def create(self, validated_data):
        user = self.context["request"].user
        initial_deposit = validated_data.pop("initial_deposit")
        account_number = BankAccount.generate_account_number()
        account = BankAccount.objects.create(
            user=user,
            account_number=account_number,
            account_type=validated_data["account_type"],
            balance=initial_deposit,
        )
        return account


class TransferSerializer(serializers.Serializer):
    from_account = serializers.CharField()
    to_account = serializers.CharField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0.01)

    def validate(self, data):
        user = self.context["request"].user
        amount = data.get("amount")

        # Default failed transaction object (for logging)
        self.failed_txn = Transaction(amount=amount, status="failed")

        # Check sender account
        try:
            from_acc = BankAccount.objects.get(
                account_number=data["from_account"], user=user
            )
        except BankAccount.DoesNotExist:
            self.failed_txn.reason = "Sender account not found."
            self.failed_txn.save()
            raise serializers.ValidationError("Sender account not found.")

        # Check recipient account
        try:
            to_acc = BankAccount.objects.get(account_number=data["to_account"])
        except BankAccount.DoesNotExist:
            self.failed_txn.from_account = from_acc
            self.failed_txn.reason = "Recipient account not found."
            self.failed_txn.save()
            raise serializers.ValidationError("Recipient account not found.")

        if from_acc.balance < amount:
            self.failed_txn.from_account = from_acc
            self.failed_txn.to_account = to_acc
            self.failed_txn.reason = "Insufficient funds."
            self.failed_txn.save()
            raise serializers.ValidationError("insufficient_funds")

        # Daily limit check
        today = timezone.now().date()
        total_transferred_today = (
            Transaction.objects.filter(
                from_account=from_acc, timestamp__date=today, status="success"
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )

        if total_transferred_today + amount > DAILY_LIMIT:
            self.failed_txn.from_account = from_acc
            self.failed_txn.to_account = to_acc
            self.failed_txn.reason = "Daily limit exceeded."
            self.failed_txn.save()
            raise serializers.ValidationError("daily_limit_exceeded")

        data["from_acc"] = from_acc
        data["to_acc"] = to_acc
        return data

    def create(self, validated_data):
        from_acc = validated_data["from_acc"]
        to_acc = validated_data["to_acc"]
        amount = validated_data["amount"]

        with db_transaction.atomic():
            from_acc.balance -= amount
            to_acc.balance += amount
            from_acc.save()
            to_acc.save()

            txn = Transaction.objects.create(
                from_account=from_acc,
                to_account=to_acc,
                amount=amount,
                status="success",
            )
        return txn


class AuditLogSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["user_id", "username", "action", "ip_address", "timestamp"]
        read_only_fields = fields  # Logs cannot be created via API
