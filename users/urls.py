from django.urls import path
from users.views import (
    RegisterView,
    PendingKYCListView,
    KYCVerifyView,
    CreateBankAccountView,
    ListBankAccountsView,
    TransferMoneyView,
    AuditLogListView,
    KYCReSubmitView,
    ResetPasswordView
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("kyc/pending/", PendingKYCListView.as_view(), name="pending_kyc"),
    path("kyc/verify/", KYCVerifyView.as_view(), name="kyc_verify"),
    path("accounts/", CreateBankAccountView.as_view(), name="create_account"),
    path("accounts/list/", ListBankAccountsView.as_view(), name="list_accounts"),
    path("transfer/", TransferMoneyView.as_view(), name="transfer_money"),
    path("audit/", AuditLogListView.as_view(), name="audit-logs"),
    path("kyc/resubmit/", KYCReSubmitView.as_view(), name="kyc_resubmit"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="reset_password"),
]
