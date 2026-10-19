# My properties 4U

![CI](https://github.com/ashtongoodmanwrk-bit/Myproperties4U/actions/workflows/ci.yml/badge.svg)
A property management platform designed for tenants to pay their rent as well as report maintenance issues and where landlords mange the properties, units and leases
Admins also audit each change
This is a full stack portfolio project focusing on a strong backend, with features such as databased enforced rules, audit trail and concurrency safe payments
**Live demo:** https://my-properties4u.onrender.com
>**Payments do not use or transfer any real money. No card details are used or stored, with all transactions being purely simulated
>
>The demo is ran on a free tier, so the API sleeps when idle, so the first request tends to take slightly longer than usual

## Demo accounts

The passwords for all the acounts are 'Demo1234!'

ROLE | EMAIL |
LANDLORD | 'landlord1@example.com', 'landlord2@example.com' |
TENANT | 'tenant1@example' to 'tenant12@example.com' |
ADMIN | 'admin@example.com |

## 



with auto-generated rent schedules, and a maintanence board

**TENANTS** lease summary, rent schedule with a pay rent button, and a maintanence request form

**ADMINS** a filterable, paginated audit log showing old and new values for every change
**BACKGROUND JOBS** overdue rent marking and upcoming rent reminders, run daily 

**ARCHITECTURE**

'''mermaid
flowchart LR
browser -> Static["react app<br/>(render static site)"]
static -- "/api/* rewrite" -> API["FastAPI<br/>(Render web service)"]
API -> DB[("PostgreSQL<br/>(neon)")]
cron["Github Actions<br/>(daily sschedule)")] -- "overdue + reminders" -> DB
'''

TECH STACK 

**Backend:** FastAPI, SQLAlchemy 2.0, Alembic, psycopg 3, Pydantic, argon2 password hashing, JWT auth, APScheduler 
**Database** PostgreSQL 16
**Frontend** React, Typescript, Vite, Tansack Query, React router, Recharts
**Devops** Docker and Docker Compose, Github Actions CI (ruff, pytest, ESLint, build), deployed on Render and neon

## DESIGN DECISIONS 
** the payments are safe to retry and race** When there is a payment, it locks the rent charge row ('SELECT ... FOR UPDATE') and it checks the idempotency key, checks the balance, then it records the payment in one entire transaction. The same key with the same payload replays the initial result. A 422 is returned for either overpayments or when its the same key with a different payload. The database backstop is a unique constraint on '(user_id, idempotency_key)'

**overlapping leases are impossible** A postgreSQL exclusion constraint ('btree_gist' with a date range) blocks any overlapping active leases on a unit, also the API shows the violation as a 409
**Every change is audited.** Lease creation, payments and maintenance changes write an audit row with old and new values (JSONB) in the same transaction as the change.
**Ownership failures return 404, not 403,** so the API doesn't reveal whether another landlord's record exists.
**Maintenance follows a strict workflow:** submitted, assigned, in progress, resolved. Skipping a step returns 409, and the row is locked while it changes.
**Dashboard figures are computed in SQL** from a database view of charge balances.
**APScheduler instead of Celery:** the jobs are small and idempotent, and a Redis broker would add infrastructure for no benefit. In production the job runs from a scheduled GitHub Actions workflow because the free hosting tier has no always-on worker. 

## RUNNING IT LOCALLY

You will need docker desktop, Node 22 and Python 3.13

'''powershell
# 1. start up the database, API on http://localhost:8000 and worker
docker compose up -d --build

# 2. create the backend environment and load demo data
cd backend
python -m venv .venv
.\.venv\scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m scripts.seed --reset

# 3. start the frontend (http://localhost:5173)
cd ..\frontend
npm ci 
npm run dev
'''

Make sure to check 'backend\.env' points at 'localhost:5432' before seeding. API docs are at 
http://localhost:8000/docs

Run the checks from 'backend' with the venv active:

'''powershell
ruff check .
ruff format --check .
pytest -v
'''

the test will use a seperate database ('property_mgmt_test') so the demo data is not touched by it

## project layout

