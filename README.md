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
