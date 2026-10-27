# Swachh PU Backend

Backend API for **Swachh PU Abhiyaan** — campus cleanliness task management system.

Built with **FastAPI** + **PostgreSQL (Neon)**.

---

## 🚀 Quick Start

Built with **FastAPI** + **PostgreSQL** (hosted on [Neon](https://neon.tech)). Supabase is no longer used:
uploaded photos and audio are stored in the database and served by the API at `/media/...`.

### 1. Create a free Neon database

1. Sign up at [neon.tech](https://neon.tech) → **Create project** (region: AWS Asia Pacific (Singapore) is closest to India).
2. Click **Connect**, tick **Connection pooling**, and copy the connection string
   (`postgresql://...-pooler...neon.tech/neondb?sslmode=require`).

### 2. Install and configure

```bash
git clone https://github.com/Monaal5/swachh-pu-backend.git
cd swachh-pu-backend
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # Windows   (macOS/Linux: cp .env.example .env)
```

Paste the Neon URL into `DATABASE_URL` in `.env`.

### 3. Create tables, campus data and an admin (one time)

```bash
python scripts/init_db.py --admin-email admin@pu.ac.in --admin-password "Admin@12345" --demo-workers
```

This creates all tables (`db/schema.sql`), loads 297 UIET rooms from the spreadsheets, creates the admin,
and (with `--demo-workers`) adds sample workers `ramesh.kumar@swachh.pu / Ramesh@101`,
`suresh.singh@swachh.pu / Suresh@102`, `anita.devi@swachh.pu / Anita@103`. Safe to run again.

### 4. Run locally

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000/health — it should say `"database": "connected"`.

### 5. Deploy on Vercel

In the Vercel project → **Settings → Environment Variables**, add `DATABASE_URL` (the Neon pooled URL) and,
optionally, the `SMTP_*` variables. Remove the old `SUPABASE_*` variables, then redeploy.
Note: Vercel limits request bodies to about 4.5 MB, so the app should compress photos before uploading.

---

## 📖 API Documentation

Once the server is running, visit:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/signup` | Register new user | ❌ |
| POST | `/auth/login` | Login | ❌ |
| POST | `/auth/logout` | Logout | ✅ |
| GET | `/auth/me` | Get current user | ✅ |

### Profiles
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/profiles/me` | Get own profile | ✅ |
| PUT | `/profiles/me` | Update own profile | ✅ |
| GET | `/profiles/workers` | List workers | ✅ Admin |
| GET | `/profiles/{id}` | Get any profile | ✅ Admin |

### Tasks
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/tasks/` | Create task | ✅ |
| GET | `/tasks/` | List tasks (filtered) | ✅ |
| GET | `/tasks/my-tasks` | Worker's assigned tasks | ✅ Worker |
| GET | `/tasks/{id}` | Get task detail | ✅ |
| PATCH | `/tasks/{id}/assign` | Assign to worker | ✅ Admin |
| PATCH | `/tasks/{id}/reject` | Reject task | ✅ Admin |
| PATCH | `/tasks/{id}/complete` | Complete task | ✅ Worker |

### Upload & Media
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/upload/photo` | Upload photo | ✅ |
| POST | `/upload/audio` | Upload audio | ✅ |
| GET | `/media/{bucket}/{path}` | Download an uploaded file | ❌ |

---

## 🗄️ Database Schema

| Table | Description |
|-------|-------------|
| `profiles` | Base user profile (name, role, phone) |
| `student_profiles` | Student details (roll_no, address, hostel) |
| `worker_profiles` | Worker details (employee_id, zone) |
| `tasks` | Task/complaint (photo, location, status, assigned_to) |

### Task Status Flow

```
pending → assigned → completed
pending → rejected
```

---

## 🏗️ Project Structure

```
app/
├── main.py              # FastAPI entry point
├── config.py            # Environment config
├── dependencies.py      # Auth middleware
├── models/              # Pydantic schemas
│   ├── auth.py
│   ├── profile.py
│   └── task.py
├── routers/             # API endpoints
│   ├── auth.py
│   ├── profiles.py
│   ├── tasks.py
│   └── upload.py
├── services/            # Supabase query logic
│   ├── auth_service.py
│   ├── profile_service.py
│   ├── task_service.py
│   └── storage_service.py
└── utils/
    └── db.py            # PostgreSQL access layer + media storage
```

---

## 🔑 Roles

| Role | Can Do |
|------|--------|
| **Student** | Create tasks, view own tasks |
| **Worker** | View assigned tasks, mark complete |
| **Admin** | View all tasks, assign, reject |
