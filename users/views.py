from django.shortcuts import render
from rest_framework import generics, permissions, status, serializers
from users.serializers import (
    UserRegisterSerializer,
    PendingKYCSerializer,
    KYCVerifySerializer,
    BankAccountCreateSerializer,
    BankAccountSerializer,
    TransferSerializer,
    AuditLogSerializer,
    KYCReSubmitSerializer,
    ResetPasswordSerializer
)
from rest_framework.response import Response
from users.models import KYC, BankAccount, AuditLog
from users.permissions import IsAdminUser, IsAuditorUser
from rest_framework.views import APIView
from users.utils import log_action, get_client_ip

# Create your views here.


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        ip = get_client_ip(self.request)
        log_action(user, "User registered", ip)


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [permissions.AllowAny]  # User may not be logged in

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Log the password reset attempt
        ip = get_client_ip(request)
        log_action(user, "password_reset", ip)

        return Response(
            {"message": "Password reset successfully."}, status=status.HTTP_200_OK
        )


class KYCReSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = KYCReSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kyc = serializer.update(
            serializer.validated_data["kyc_instance"], serializer.validated_data
        )

        # Audit logging
        ip = get_client_ip(request)
        log_action(request.user, f"Re-submitted KYC (id={kyc.id})", ip)

        return Response(
            {
                "kyc_id": kyc.id,
                "status": kyc.status,
                "message": "KYC re-submitted successfully.",
            },
            status=status.HTTP_200_OK,
        )


# --- List Pending KYC ---
class PendingKYCListView(generics.ListAPIView):
    serializer_class = PendingKYCSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        return KYC.objects.filter(status="pending").order_by("submitted_at")


# --- Verify/Reject KYC ---
class KYCVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = KYCVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        kyc_id = serializer.validated_data["kyc_id"]
        status_value = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")

        try:
            kyc = KYC.objects.get(id=kyc_id)
        except KYC.DoesNotExist:
            return Response({"error": "KYC not found"}, status=404)

        kyc.status = status_value
        kyc.notes = notes
        kyc.save()

        # Update user kyc_verified flag if approved, leave False if rejected
        if status_value == "verified":
            kyc.user.kyc_verified = True
            message = "KYC approved successfully."
        else:
            kyc.user.kyc_verified = False
            message = "KYC rejected successfully."

        kyc.user.save()

        ip = get_client_ip(request)
        log_action(request.user, f"KYC {status_value} for user {kyc.user.username}", ip)

        return Response(
            {
                "kyc_id": kyc.id,
                "user_id": kyc.user.id,
                "status": kyc.status,
                "message": message,
            }
        )


class CreateBankAccountView(generics.CreateAPIView):
    serializer_class = BankAccountCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        account = serializer.save()
        ip = get_client_ip(self.request)
        log_action(
            self.request.user, f"Created bank account {account.account_number}", ip
        )


class ListBankAccountsView(generics.ListAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)


class TransferMoneyView(generics.CreateAPIView):
    serializer_class = TransferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        ip = get_client_ip(request)
        try:
            serializer.is_valid(raise_exception=True)
            txn = serializer.save()
            log_action(
                request.user,
                f"Transferred {txn.amount} from {txn.from_account.account_number} "
                f"to {txn.to_account.account_number}",
                ip,
            )
            return Response(
                {
                    "transaction_id": str(txn.transaction_id),
                    "status": txn.status,
                    "message": "Transfer completed successfully.",
                }
            )
        except serializers.ValidationError as e:
            errors = e.detail

            # Extract non_field_errors if they exist
            if isinstance(errors, dict) and "non_field_errors" in errors:
                error_list = errors["non_field_errors"]
                if "insufficient_funds" in error_list:
                    return Response({"error": "Insufficient funds."}, status=400)
                elif "daily_limit_exceeded" in error_list:
                    return Response({"error": "Daily limit exceeded."}, status=400)

            # fallback
            log_action(request.user, f"Transfer failed: {error_message}", ip)
            return Response({"error": errors}, status=400)


class AuditLogListView(generics.ListAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsAuditorUser,
    ]  # Only auditors can access
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all()
