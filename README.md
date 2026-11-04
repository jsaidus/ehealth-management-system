# E-Health MVP v2

A Streamlit prototype for finding health services, checking pharmacy inventory, booking appointments, and keeping personal health readings.

## Phase 2 upgrades
- Password authentication using PBKDF2-HMAC-SHA256
- Role-based access: Subscriber, Facility Admin, System Admin
- Session login/logout
- Redesigned dashboard/navigation
- Facility map from stored coordinates
- Subscriber-only appointments and private readings
- Facility Admin appointment management and pharmacy inventory
- System Admin facility/user management
- Existing SQLite schema/data remains compatible

## Run on Pop!_OS

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
cd ~/Desktop/ehealth_mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the Local URL shown by Streamlit, normally `http://localhost:8501`.

## First run
The login sidebar shows **First-time system setup** only while there is no System Admin. Create the first admin with a password of at least 10 characters, then log in.

Existing subscriber rows from v1 are preserved, but they do not automatically have passwords. Create a new subscriber account for testing v2.

## Important
This is an educational MVP, not a production medical system. A real deployment needs security/privacy review, encryption and secrets management, audit logs, identity verification, backups, regulatory review, accessibility testing, and validated workflows/devices for clinical data.
