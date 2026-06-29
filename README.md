# Wittyfluence - Instagram Scraper & Analytics

Wittyfluence is a FastAPI-powered backend with a beautiful frontend dashboard designed to retrieve and analyze Instagram profile engagement data. It leverages Scrapling and Playwright for stealthy web crawling, utilizes proxy pools, and computes rich engagement metrics for Instagram profiles.

## Features

- **Profile Scraper & Analytics**: Fetches profile data, post details, engagement rates, and recent posts.
- **Stealth Browsing**: Leverages Scrapling and Playwright with stealth configurations to bypass bot detection.
- **Proxy Rotation**: Automatically fetches and rotates free HTTP proxies.
- **FastAPI Backend**: Clean and efficient REST API serving both data endpoints and the UI.
- **Beautiful Frontend**: Sleek dashboard serving index.html, index.css, and main.js directly.

---

## Prerequisites

- **Python**: version `3.11` is recommended (tested on Python `3.11.9`).
- **Operating System**: macOS, Linux, or Windows.
- **Network**: Internet access (required to download browser binaries and make proxy requests).

---

## Installation & Setup

Follow these steps to set up and run the application on any other system.

### 1. Clone the Repository
```bash
git clone https://github.com/reachout2utkarshsingh/wittyfluence.git
cd wittyfluence
```

### 2. Set Up a Virtual Environment
It is highly recommended to run the app inside a virtual environment:

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Python Dependencies
Install the required packages listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Install Playwright Web Browsers
Playwright requires browser binaries to execute the headless scraper:
```bash
playwright install --with-deps
```

---

## Running the Application

Start the FastAPI application using Uvicorn. The app is configured to serve the frontend directly.

```bash
uvicorn app:app --reload
```

Once started, open your browser and navigate to:
**[http://localhost:8000](http://localhost:8000)**

---

## Folder Structure

- `app.py`: Main FastAPI backend application containing scraping routes and analytic calculations.
- `index.html`, `index.css`, `main.js`: Vanilla frontend assets served at the root `/` endpoint.
- `requirements.txt`: Python package dependencies.
- `runtime.txt`: Python version specification.
