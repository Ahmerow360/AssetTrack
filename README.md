# AssetTrack – IT Asset Management System

A lightweight web app built with Python (Flask) to manage IT assets, track issues, and record deployments.

---

## Features

- Auto-generated unique Asset IDs (e.g. `KW-LAP-0001`, `KW-SRV-0003`)
- Asset register with category, location, assigned user, serial number
- Install date & warranty expiry tracking with alerts
- Issue / incident log with severity levels (Critical, High, Medium, Low)
- Resolve issues with notes
- Deployment history for each asset
- Search and filter assets
- Export all assets to CSV
- Dashboard with summary stats

---

## Setup Instructions

### 1. Install Python (3.9 or higher)
Download from https://python.org

### 2. Install Flask
Open terminal/command prompt in this folder and run:
```
pip install flask
```

### 3. Run the App
```
python app.py
```

### 4. Open in Browser
Go to: http://localhost:5000

---

## Project Structure

```
assettrack/
├── app.py              ← Main Flask application
├── requirements.txt    ← Python dependencies
├── assettrack.db       ← SQLite database (auto-created)
└── templates/
    ├── base.html       ← Sidebar + navigation layout
    ├── dashboard.html  ← Home dashboard
    ├── assets.html     ← Assets list with search/filter
    ├── asset_form.html ← Add / Edit asset form
    ├── asset_detail.html ← Asset detail + issues + deployments
    ├── issues.html     ← Issues list
    └── issue_form.html ← Log new issue
```

---

## Asset ID Format

`KW-{CATEGORY}-{NUMBER}`

| Category | Code |
|----------|------|
| Laptop | LAP |
| Server | SRV |
| Network | NET |
| Printer | PRT |
| UPS | UPS |
| Desktop | DSK |
| Other | OTH |

Example: `KW-SRV-0003` = 3rd server registered

---

## Adding More Features Later

- **User login**: Add `flask-login` library
- **Email alerts for warranty**: Add `smtplib` with a scheduler
- **QR code per asset**: Add `qrcode` library  
- **More reports**: Extend the dashboard route in `app.py`
