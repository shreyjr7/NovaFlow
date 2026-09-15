# Deploying NovaFlow to Supabase (Database) & Vercel (Frontend)

This guide walks you through deploying **NovaFlow Transport** with a **Supabase PostgreSQL database** and a **Vercel frontend**.

---

## Part 1: Supabase Setup (PostgreSQL Database)

### 1. Create a Project on Supabase
1. Go to https://supabase.com/ and sign in.
2. Click **New project**.
3. Set project name: 
ovaflow-transport
4. Set a secure database password (save this password).
5. Choose your preferred region (e.g. p-south-1 Mumbai).

### 2. Copy the Database Connection String
1. Go to **Project Settings** -> **Database**.
2. Scroll to **Connection string** -> Select **URI**.
3. Format will look like:
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?pgbouncer=true
   *(Or direct port 5432: postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres)*

### 3. Connect NovaFlow to Supabase
In your backend environment (or root .env):
`env
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
NOVAFLOW_DEV_MODE=true
`
When the backend starts up, it will automatically connect, generate all tables (ingested_events), and seed the historical records.

---

## Part 2: Deploy Frontend to Vercel

The frontend has already been pre-configured with rontend/vercel.json for single-page application (SPA) client-side routing.

### Option A: Deploy via GitHub (Recommended)
1. Push your repository to GitHub.
2. Go to https://vercel.com/ -> Click **Add New...** -> **Project**.
3. Import your GitHub repository.
4. Set the **Root Directory** to rontend.
5. Framework Preset: **Vite** (auto-detected).
6. Build Command: ite build (or 
pm run build).
7. Output Directory: dist.
8. Under **Environment Variables**, add:
   - VITE_GOOGLE_MAPS_API_KEY: *(Your Google Maps API key, optional)*
   - VITE_API_BASE_URL: *(Your deployed backend URL, e.g. from Render/Railway)*
9. Click **Deploy**.

### Option B: Deploy via Vercel CLI
From your terminal:
`ash
cd frontend
npm install -g vercel
vercel
`
Follow the prompts, select dist as the build output, and deployment will complete in under 60 seconds.

---

## Part 3: Deploy Backend (Render / Railway / Fly.io)

Since Vercel is designed for static assets and serverless functions, the full FastAPI streaming server runs best on **Render**, **Railway**, or **Fly.io** connected to your Supabase PostgreSQL:

### Deploying to Render:
1. Go to https://render.com/ -> **New Web Service**.
2. Connect your repository.
3. Root Directory: .
4. Runtime: Python 3
5. Build Command: pip install -r requirements.txt
6. Start Command: uvicorn backend.app.main:app --host 0.0.0.0 --port 
7. In **Environment Variables**:
   - DATABASE_URL: *(Your Supabase connection string from Part 1)*
   - PYTHONPATH: edge/src:.
   - NOVAFLOW_DEV_MODE: 	rue

Once deployed, copy your Render backend URL (e.g. https://novaflow-backend.onrender.com) and paste it into Vercel as VITE_API_BASE_URL.
