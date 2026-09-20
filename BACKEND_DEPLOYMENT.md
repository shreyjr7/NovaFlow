# NovaFlow Backend Deployment & Vercel Connection Guide

This guide explains how to connect your **NovaFlow Vercel Frontend** to the **FastAPI AI Backend**.

---

## ⚡ Option 1: Instant 30-Second Live Connection (Fastest)

If you are running the backend on your laptop/PC and want your live Vercel app to connect to it immediately:

### Step 1: Ensure Local Backend is Running
In your project root:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

### Step 2: Open a Secure HTTPS Tunnel
In another terminal, run:
```bash
npx localtunnel --port 8000
```
*(Alternatively, you can use `ngrok http 8000`)*

Localtunnel will output a public HTTPS URL, for example:
```
your url is: https://gentle-fox-42.loca.lt
```

### Step 3: Connect in NovaFlow
1. Open your Vercel deployment in your browser (e.g., `https://novaflow-...vercel.app`).
2. Go to **AI Road Scan** (`/scan`) or click **AI Server (Configure)** in the top navigation header.
3. Paste your tunnel URL (`https://gentle-fox-42.loca.lt`) into the **Backend Endpoint URL** field.
4. Click **Connect & Save**.
5. The status indicator turns **Green (AI Server Connected)**, and your live Vercel app is now actively performing AI road defect analysis powered by your machine!

---

## ☁️ Option 2: 24/7 Free Cloud Deployment (Render.com)

If you want the backend to run 24/7 in the cloud without needing your laptop powered on:

### Step 1: Create a Free Web Service on Render
1. Go to [Render.com](https://render.com) and click **New + > Web Service**.
2. Connect your GitHub repository: `shreyjr7/NovaFlow`.
3. Set the following settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Click **Create Web Service**. Render will deploy the backend and give you an HTTPS URL (e.g. `https://novaflow-backend.onrender.com`).

### Step 2: Configure Vercel Environment Variable
1. Go to [Vercel Dashboard](https://vercel.com) > Select your NovaFlow project.
2. Navigate to **Settings > Environment Variables**.
3. Add a new variable:
   - **Key**: `VITE_API_URL`
   - **Value**: `https://novaflow-backend.onrender.com` (your Render URL)
4. Redeploy on Vercel (or trigger a new build by pushing to GitHub).
5. Now, every user visiting your Vercel link connects automatically to your cloud backend without any manual configuration!

---

## 🛠️ Architecture Summary

```
[Vercel Web App (SPA)]
   │
   │ (HTTPS fetch with transparent Interceptor)
   ▼
[Backend Endpoint]
   ├── Localtunnel / Ngrok (Local PC for rapid judging/testing)
   └── Render / Railway Cloud Host (24/7 production)
         │
         ├── FastAPI REST Endpoints (/api/v1/analyze/...)
         ├── PyTorch YOLOv8 Dual-Engine Detector (Potholes, Cracks, Signs, Road Damage)
         └── SQLite / PostgreSQL Persistence & Telemetry
```
