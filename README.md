# Finance Data Processing and Access Control

A production-grade backend for a **finance dashboard system** built with **FastAPI**, **Clean Architecture**, and **Role-Based Access Control (RBAC)**. Designed as an assignment submission for Zorvyn.

---

## 🏗️ Architecture

This project follows **Clean Architecture** principles with strict layer separation:

```
app/
├── core/           → Configuration, security, constants, exceptions
├── domain/         → ORM models (User, FinancialRecord) and database
├── repositories/   → Data access layer (abstract base + concrete implementations)
├── services/       → Business logic (auth, user, records, dashboard)
├── api/            → Presentation layer (routes, schemas/DTOs, dependencies/RBAC)
└── middleware/     → Error handlers
```

**Dependency Rule**: Inner layers (domain, services) never depend on outer layers (API, infrastructure). Services depend on repository abstractions, not concrete DB implementations.

### SOLID Principles

| Principle | How It's Applied |
|---|---|
| **Single Responsibility** | Each layer has one job — routes handle HTTP, services handle logic, repos handle data |
| **Open/Closed** | New roles/permissions are added via the data-driven permission matrix without modifying enforcement logic |
| **Liskov Substitution** | Repository interfaces allow swapping SQLite ↔ PostgreSQL without breaking services |
| **Interface Segregation** | Separate schemas for create/update/response — clients never see internal fields |
| **Dependency Inversion** | Services depend on repository abstractions, not concrete implementations |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/Nishanth-nishu/Finance-Data-Processing-and-Access-Control.git
cd Finance-Data-Processing-and-Access-Control

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env to set a secure JWT_SECRET_KEY for production

# Start the server
uvicorn main:app --reload --port 8001
```

### Access the API

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **Health Check**: http://localhost:8001/health

---

## 🔐 Authentication & Authorization

### Authentication Flow

1. **Register** → `POST /api/v1/auth/register` (creates user with `viewer` role)
2. **Login** → `POST /api/v1/auth/login` (returns access + refresh tokens)
3. **Use Token** → Include `Authorization: Bearer <access_token>` header
4. **Refresh** → `POST /api/v1/auth/refresh` (get new access token)

### Role-Based Access Control (RBAC)

Access is enforced via a **data-driven permission matrix** — no hardcoded if-else checks.

| Endpoint | Viewer | Analyst | Admin |
|---|:---:|:---:|:---:|
| View records | ✅ | ✅ | ✅ |
| View recent activity | ✅ | ✅ | ✅ |
| View dashboard summary | ❌ | ✅ | ✅ |
| View trends & categories | ❌ | ✅ | ✅ |
| Create/Update/Delete records | ❌ | ❌ | ✅ |
| Manage users & roles | ❌ | ❌ | ✅ |

---

## 📡 API Endpoints

### Authentication
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Public | Register new user |
| POST | `/api/v1/auth/login` | Public | Login, get tokens |
| POST | `/api/v1/auth/refresh` | Bearer | Refresh access token |

### User Management
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me` | Any role | Get own profile |
| GET | `/api/v1/users` | Admin | List all users (paginated) |
| GET | `/api/v1/users/{id}` | Admin | Get user by ID |
| PATCH | `/api/v1/users/{id}` | Admin | Update user profile |
| PATCH | `/api/v1/users/{id}/role` | Admin | Assign role |
| PATCH | `/api/v1/users/{id}/status` | Admin | Activate/deactivate |

### Financial Records
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/records` | Admin | Create record |
| GET | `/api/v1/records` | Viewer+ | List records (filtered, paginated) |
| GET | `/api/v1/records/{id}` | Viewer+ | Get single record |
| PUT | `/api/v1/records/{id}` | Admin | Update record |
| DELETE | `/api/v1/records/{id}` | Admin | Soft-delete record |

**Filters**: `?type=income&category=salary&date_from=2026-01-01&date_to=2026-12-31&search=bonus&page=1&page_size=20`

### Dashboard Analytics
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/dashboard/summary` | Analyst+ | Total income/expenses/balance |
| GET | `/api/v1/dashboard/categories` | Analyst+ | Category-wise breakdown |
| GET | `/api/v1/dashboard/recent` | Viewer+ | Recent activity |
| GET | `/api/v1/dashboard/trends` | Analyst+ | Monthly income/expense trends |

---

## 🗄️ Data Model

### User
| Field | Type | Notes |
|---|---|---|
| id | int | Auto-increment PK |
| email | string | Unique, indexed |
| username | string | Unique, indexed |
| hashed_password | string | bcrypt hashed |
| full_name | string | Optional |
| role | enum | viewer, analyst, admin |
| status | enum | active, inactive |
| created_at | datetime | UTC timestamp |
| updated_at | datetime | UTC, auto-updated |

### Financial Record
| Field | Type | Notes |
|---|---|---|
| id | int | Auto-increment PK |
| amount | float | Must be positive |
| type | enum | income, expense |
| category | string | Indexed |
| record_date | date | Indexed |
| description | text | Optional |
| created_by | int | FK → users.id |
| is_deleted | bool | Soft delete flag |
| created_at | datetime | UTC timestamp |
| updated_at | datetime | UTC, auto-updated |

---

## ✅ Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_users.py -v
python -m pytest tests/test_financial_records.py -v
python -m pytest tests/test_dashboard.py -v
```

**Test Coverage: 41 tests across 4 modules**

| Module | Tests | What's Covered |
|---|---|---|
| `test_auth.py` | 11 | Register (validation, duplicates), login, token refresh |
| `test_users.py` | 6 | RBAC on user endpoints, role assignment, status management |
| `test_financial_records.py` | 13 | CRUD, filtering, RBAC, soft delete |
| `test_dashboard.py` | 11 | Summary accuracy, RBAC on analytics endpoints |

---

## 🛡️ Error Handling

All errors return structured JSON with appropriate HTTP status codes:

```json
{
  "error": {
    "message": "User not found",
    "detail": "User with identifier '99' does not exist.",
    "type": "EntityNotFoundError"
  }
}
```

| Status | Meaning |
|---|---|
| 401 | Authentication failed (invalid/missing token) |
| 403 | Authorization failed (insufficient permissions) |
| 404 | Entity not found |
| 409 | Duplicate entity (email/username taken) |
| 422 | Validation error (invalid input) |
| 500 | Internal server error (no details leaked) |

---

## 🔧 Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| Framework | FastAPI | Async, auto OpenAPI docs, built-in DI |
| Database | SQLite + aiosqlite | Easy to swap for PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) | Industry standard, type-safe |
| Auth | JWT (python-jose) | Stateless, industry standard |
| Hashing | bcrypt | Gold standard for password storage |
| Validation | Pydantic v2 | Fast, schema-based validation |
| Testing | pytest + pytest-asyncio | Async test support with in-memory DB |

---

## 📁 Project Structure

```
Finance-Data-Processing-and-Access-Control/
├── app/
│   ├── core/
│   │   ├── config.py              # Environment-based settings (pydantic-settings)
│   │   ├── constants.py           # Enums, permission matrix
│   │   ├── exceptions.py          # Custom exception hierarchy
│   │   └── security.py            # JWT + bcrypt utilities
│   ├── domain/
│   │   ├── database.py            # Async engine, session, base
│   │   └── models/
│   │       ├── user.py            # User ORM model
│   │       └── financial_record.py # Financial record ORM model
│   ├── repositories/
│   │   ├── base.py                # Abstract repository pattern
│   │   ├── user_repository.py     # User data access
│   │   └── financial_record_repository.py  # Records + aggregations
│   ├── services/
│   │   ├── auth_service.py        # Registration, login, refresh
│   │   ├── user_service.py        # User CRUD, role/status mgmt
│   │   ├── financial_record_service.py    # Records CRUD + filtering
│   │   └── dashboard_service.py   # Analytics aggregations
│   ├── api/
│   │   ├── dependencies.py        # RBAC: PermissionChecker, RoleChecker
│   │   ├── schemas/               # Pydantic DTOs
│   │   └── v1/                    # Versioned route handlers
│   └── middleware/
│       └── error_handler.py       # Global exception → HTTP mapping
├── tests/                         # 41 tests across 4 modules
├── main.py                        # Composition root
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📝 Design Decisions & Assumptions

1. **SQLite for simplicity** — easily swappable to PostgreSQL by changing `DATABASE_URL`
2. **Default role is `viewer`** — new users start with minimum privileges
3. **Soft delete for financial records** — records are never physically removed (audit compliance)
4. **Categories are free-text** — not enforced from a fixed list for flexibility
5. **Permission matrix is data-driven** — adding new roles/permissions requires no code changes to enforcement logic
6. **No admin seeding** — first admin must be promoted via database or a future admin bootstrap endpoint
7. **Monthly trends use SQLite `strftime`** — swap to `EXTRACT` for PostgreSQL

---

## 📜 License

MIT
