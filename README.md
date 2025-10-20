**Author:** Muhammad Ahmad El-kufahn  
**Email:** muhammadelkufahn27@gmail.com  
**Stack:** Python / Django / DRF
# 🧩 Backend Wizards — Stage 1: String Analyzer API

A RESTful API built with **Python (Django + DRF)** that analyzes strings, stores their computed properties, and supports natural language filtering.

---

## 🚀 Features

✅ Analyze strings and compute:
- Length  
- Palindrome check  
- Unique characters  
- Word count  
- SHA-256 hash  
- Character frequency map  

✅ Endpoints:
- `POST /string` → Analyze and store a string  
- `GET /strings/<value>` → Retrieve details of a string  
- `GET /strings/` → List all strings with optional filters  
- `GET /strings/filter-by-natural-language?query=<phrase>` → Query using natural language  
- `DELETE /string/<value>/delete` → Delete a stored string  

---

## 🧠 Example Response

```json
{
  "id": "0a4f0b2b...",
  "value": "hello world",
  "properties": {
    "length": 11,
    "is_palindrome": false,
    "unique_characters": 8,
    "word_count": 2,
    "sha256_hash": "0a4f0b2b...",
    "character_frequency_map": {"h":1,"e":1,"l":3,"o":2,"w":1,"r":1,"d":1}
  },
  "created_at": "2025-10-20T12:00:00Z"
}
```


# Backend Wizards — Stage 0 Task


---

## Overview

This project implements the **Stage 0 backend task** — a REST API endpoint `/me` that returns:

-  Profile information
-  Current UTC timestamp
-  A random cat fact fetched dynamically from the Cat Facts API

Example response:

```json
{
	"status": "success",
	"user": {
		"email": "muhammadelkufahn27@gmail.com",
		"name": "Muhammad Ahmad El-kufahn",
		"stack": "Python/Django"
	},
	"timestamp": "2025-10-16T10:50:56.518856+00:00",
	"fact": "A cat will tremble or shiver when it is extreme pain."
}
```

---

## Repository

Source: https://github.com/KhalifahMB/HNG13_Intenship.git

## Run locally (development)

Prerequisites:

-  Python 3.12+
-  A virtualenv
-  Git

Steps:

### 1. Clone the repository

```powershell
git clone https://github.com/KhalifahMB/HNG13_Intenship.git
cd HNG13_Intenship
```

### 2. Create and activate a virtual environment (PowerShell-Windows):

```powershell
python -m venv venv
& .\venv\Scripts\Activate.ps1
```

### 3. Install dependencies from `requirements.txt`:

```powershell
pip install -r requirements.txt
```

### 4. Set required environment variables:

-  SECRET_KEY = 'your-secret-key-here'
-  DEBUG = 'True' for development only
-  ALLOWED_HOSTS = comma-separated list of host
-  DATABASE_URL = 'postgres://USER:PASS@HOST:PORT/DBNAME'
-  CORS_ALLOWED_ORIGINS = comma-separated list of host of allowed origins
-  CSRF_TRUSTED_ORIGINS = localhost, hosting server ...

### 5. Apply migrations and run the server:

```powershell
python manage.py migrate
python manage.py runserver
```

### 6. Open the `/me` endpoint:

Visit http://127.0.0.1:8000/me/

Notes:

-  For production, never set `DEBUG=True` and never use `ALLOWED_HOSTS='*'` without proper precautions.
