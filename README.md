# hcl-hackathon

# Overview
A secure Django REST API backend for a modular banking system.
It supports customer onboarding (with KYC), account management, money transfers, and audit logging — with built-in bcrypt password hashing and role-based access control.

# Actors
| Actor          | Description                                               |
| -------------- | --------------------------------------------------------- |
| **Customer**   | Register, upload KYC, create accounts, and make transfers |
| **Bank Admin** | Manage users and approve KYC                              |
| **Auditor**    | View system audit logs (read-only)                        |

# Key Features
1) Secure Authentication – JWT tokens + bcrypt password hashing
2) KYC Integration – Upload and verify customer identity documents
3) Account Management – Create savings/current/fixed deposit accounts
4) Money Transfer – Safe, validated transfers between accounts
5) Audit Logging – Every action logged with user, timestamp, and IP
6) Role-Based Access Control (RBAC) – Restrict endpoints by role

# Tech Stack

1) Backend: Django + Django REST Framework
2) Auth: JWT (djangorestframework-simplejwt)
3) Password Hashing: bcrypt
4) Database: MySQL
5) Storage: Local for KYC documents

# Security Features
**1. Password Hashing (bcrypt)**

All user passwords are hashed using bcrypt before storage.
Bcrypt adds a salt automatically.

Even if the DB is compromised, raw passwords cannot be recovered.

**2. Role-Based Access Control (RBAC)**

| Role         | Permissions                                      |
| ------------ | ------------------------------------------------ |
| **Customer** | Manage own profile, KYC, accounts, and transfers |
| **Admin**    | Manage all customers, approve KYC                |
| **Auditor**  | Read-only access to audit logs                   |

# API Documentation
**1. Register User (with KYC)**

POST /api/v1/auth/register/

Registers a new customer and uploads KYC documents in one request.

**Headers**

Content-Type: multipart/form-data


**Form Data**

| Field           | Type   | Description                      |
| --------------- | ------ | -------------------------------- |
| `username`      | string | Unique username                  |
| `email`         | string | Email address                    |
| `password`      | string | Account password (bcrypt-hashed) |
| `full_name`     | string | Customer’s full name             |
| `document_type` | string | e.g. `passport`, `id_card`       |
| `file`          | file   | KYC document (PDF/JPG/PNG)       |


**Response**

```json
{
  "user": {
    "id": 1,
    "username": "alice",
    "email": "alice@example.com",
    "role": "customer",
    "kyc_verified": false
  },
  "kyc": {
    "document_type": "passport",
    "status": "pending"
  },
  "message": "User registered successfully. KYC pending verification."
}
```

**2. Login (JWT)**

POST /api/v1/auth/token/

**Request**

```json
{
  "username": "alice",
  "password": "StrongPass123"
}
```

**Response**

```json
{
  "access": "<ACCESS_TOKEN>",
  "refresh": "<REFRESH_TOKEN>"
}
```

**3. Create Bank Account**

POST /api/v1/accounts/

**Headers**

Authorization: Bearer <ACCESS_TOKEN>


**Request**

```json
{
  "account_type": "savings",
  "initial_deposit": "100.00"
}
```

**Response**

```json
{
  "account_number": "1234567890",
  "account_type": "savings",
  "balance": "100.00"
}
```

**4. Transfer Money**

POST /api/v1/transfer/

**Headers**

Authorization: Bearer <ACCESS_TOKEN>


**Request**

```json
{
  "from_account": "1234567890",
  "to_account": "9876543210",
  "amount": "250.00"
}
```

**Response (Success)**

```json
{
  "transaction_id": "uuid-1234",
  "status": "success",
  "message": "Transfer completed successfully"
}
```

**Error Examples**

```json
{"error": "insufficient_funds"}
```

```json
{"error": "daily_limit_exceeded"}
```

**5. View Audit Logs (Auditor only)**

GET /api/v1/audit/

**Headers**

Authorization: Bearer <AUDITOR_TOKEN>


**Response**

```json
[
  {
    "user_id": 1,
    "action": "transfer_initiated",
    "ip": "192.168.1.5",
    "timestamp": "2025-10-26T12:40:00Z"
  },
  {
    "user_id": 2,
    "action": "kyc_verified",
    "ip": "192.168.1.10",
    "timestamp": "2025-10-26T12:45:00Z"
  }
]
```
**6. List pending KYC submissions**

GET /api/v1/kyc/pending/
**Role: admin only**

**Response**

```json [
  {
    "kyc_id": 7,
    "user_id": 12,
    "username": "alice",
    "full_name": "Alice Doe",
    "document_type": "passport",
    "file_url": "/media/kyc/2025/10/26/alice-passport.jpg",
    "status": "pending",
    "submitted_at": "2025-10-26T08:20:00Z"
  }
]
```
**7. Approve or reject KYC**

POST /api/v1/kyc/verify/
**Role: admin only**
**Request**
```json
{
  "kyc_id": 7,
  "status": "verified",
  "notes": "Photo ID and address verified."
}
```
```json
{
  "kyc_id": 7,
  "status": "rejected",
  "notes": "Blurry image. Please re-upload."
}
```
**Response**
```json
{
  "kyc_id": 7,
  "user_id": 12,
  "status": "verified",
  "message": "KYC approved successfully."
}
```

# Setup Instructions
git clone <repo-url>
cd modular-banking-backend

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# .env
DJANGO_SECRET_KEY=secret

DATABASE_URL=mysql://user:pass@localhost:3306/bankdb

JWT_SECRET=myjwtsecret

DEBUG=True
