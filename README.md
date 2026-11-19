# CivicCycle - Backend API

CivicCycle is a doorstep dry-waste recycling platform built with Django REST Framework. It connects citizens who want to dispose of dry waste with verified municipal ward collectors, overseen by an admin dashboard.

- **Live Website:** https://civiccycle-frontend.vercel.app
- **Frontend Repository:** https://github.com/nishadbk951/civiccycle-frontend

## Core Workflow

1. **AI Waste Verification:** When a citizen uploads a waste photo, the backend validates it through the Google Gemini API before creating a request. Valid dry waste is sorted into 7 categories (`PLASTIC`, `METAL`, `PAPER`, `E_WASTE`, `FURNITURE`, `GLASS`, or `TEXTILE`), while wet, mixed, or non-recyclable waste is rejected.
2. **Citizen Flow:** Citizens pin their doorstep GPS location, capture a photo, and receive a unique 4-digit handover PIN once a collector accepts the pickup.
3. **Collector Flow:** Collectors register with their ID card and assigned ward/municipality. After admin approval, they can view local requests, navigate via Google Maps, and complete pickups by verifying the citizen's 4-digit PIN at the doorstep.
4. **Admin Command Center:** Administrators review and approve/revoke collector accounts, filter pickups by district, municipality, or ward, reopen stuck `IN_PROGRESS` tasks, and track waste analytics.

## Engineering Challenges Solved

- **Memory Optimization on Render (512MB RAM Limit):** High-resolution mobile camera photos initially caused Gunicorn `SIGKILL` (Out-of-Memory) crashes. Solved this by tuning Gunicorn to single-worker mode (`--workers 1 --threads 2 --max-requests 200`), decoding large JPEGs at reduced resolution (`512x512`) using Pillow's `draft()` mode, and freeing image buffers immediately after processing.
- **AI Model Resilience:** Added dynamic model discovery (`client.models.list()`) with automatic fallback and retry logic (`404`, `429`, `503`) so API model updates or temporary traffic spikes do not interrupt uploads.

## Security & Demo Mode Architecture

- **Authentication & Access Control:** Phone number and password login secured with JWT tokens (`djangorestframework-simplejwt`), PBKDF2 password hashing, and role-based permissions (`USER`, `COLLECTOR`, `ADMIN`).
- **Protected Demo Admin Account:** Password changes (`POST /api/admin/change-password/`) are blocked (`403 Forbidden`) for shared demo admin phone numbers so recruiters can explore the dashboard without locking the account.
- **Environment & CORS Security:** Database credentials, AWS S3 keys, Gemini API keys, and Django secrets are managed via environment variables. CORS is restricted to the deployed frontend URL.
- **Note on Phone OTP & Collector KYC (Demo vs Production):** To allow recruiters and reviewers to test the full Citizen -> Collector -> Admin flow without barriers, phone login currently uses standard credentials instead of paid SMS OTP, and Collector ID verification uses manual admin approval. In a production environment, these endpoints are structured to integrate directly with an SMS OTP provider (such as Twilio or MSG91) and official KYC verification APIs.

## Demo Login Credentials (For Reviewers)

Use these accounts on the [Live Website](https://civiccycle-frontend.vercel.app) to test all three roles:

- **Citizen (User):** Phone: `[1122334455]` | Password: `[dilshad123]`
- **Collector:** Phone: `[1112223334]` | Password: `[sinan@123]`
- **Admin (Demo):** Phone: `[9999999990]` | Password: `[admin999]` *(Password updates locked on this shared account)*

## Tech Stack

- **Backend:** Python, Django, Django REST Framework
- **Database:** Neon PostgreSQL
- **Media Storage:** AWS S3 (`django-storages`, `boto3`)
- **AI & Image Processing:** Google GenAI SDK (`google-genai`), Pillow
- **Hosting:** Render (Gunicorn)

## Main API Endpoints

- `POST /api/register/` - Register Citizen or Collector account
- `POST /api/login/` - Phone and password JWT login
- `POST /api/pickups/request/` - AI-verified pickup submission + AWS S3 upload
- `GET /api/pickups/my-requests/` - Citizen pickup history and 4-digit handover PIN
- `GET /api/pickups/collector/assigned/` - Ward-filtered pickup queue for collectors
- `PATCH /api/pickups/collector/accept/<id>/` - Accept pickup and generate 4-digit PIN
- `PATCH /api/pickups/collector/reject/<id>/` - Decline pickup with reason
- `PATCH /api/pickups/collector/complete/<id>/` - Verify 4-digit PIN and complete job
- `GET /api/admin/collectors/` & `PATCH /api/admin/collectors/<id>/verify/` - Collector KYC approval/revocation
- `GET /api/pickups/admin/all-requests/` & `GET /api/pickups/admin/analytics/` - Request explorer and analytics
- `POST /api/admin/change-password/` - Primary admin password update

## Run Locally on Your Machine

If you want to clone and run this backend locally instead of using the hosted Render API:

1. **Download the code and install packages:**
   ```bash
   git clone https://github.com/nishadbk951/civiccyle-backend.git
   cd civiccyle-backend
   python -m venv myenv
   myenv\Scripts\activate  # On Mac/Linux: source myenv/bin/activate
   pip install -r requirements.txt
   
   2. **Add your `.env` file** in the main project folder (same folder as `manage.py`) with your own keys:
   ```env
   SECRET_KEY=your_django_secret_key
   DATABASE_URL=your_postgres_database_url
   GEMINI_API_KEY=your_google_gemini_api_key
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   AWS_STORAGE_BUCKET_NAME=your_s3_bucket_name
   ```

3. **Set up the database and start the server:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
