# 🏛️ SAHANANETH | Disaster Relief Management System
## 📖 Comprehensive User & Operations Manual

---

## 🌐 System Overview

**SAHANANETH** is an integrated, multi-tiered enterprise relief-management framework designed to streamline operations during critical emergency situations. By uniting citizens, ground units, logistics managers, and state administrators into a singular digital ecosystem, the system minimizes response latencies and optimizes resource distribution.

---

## 1. System Architecture & Entry Points

Upon initializing the platform, users are presented with a unified landing page mapping out two core operations gateways. Selecting a gateway routes the user through targeted authentication streams.

```
[ SAHANANETH Core Landing Page (/) ]
                    │
     ┌──────────────┴──────────────┐
     ▼                             ▼
[ Citizen Portal ]            [ Staff Portal ]
(/citizen/login)              (/auth/login)
│                             │
▼                             ├──────────────────────┬──────────────────────┐
Shelter Requests              ▼                      ▼                      ▼
Profile Auditing        [Gov. Officer]          [Field Officer]        [Warehouse Mgr]
Oversight & Budgets      Ground Intake          Supply Chain
```

### 🛣️ Route & Interface Mapping

| Interface Component | Access Path | Primary Objective | Target Audience |
| :--- | :--- | :--- | :--- |
| **Main Gateway** | `/` | Portal Selection & System Hub | All Users |
| **Citizen Authentication** | `/citizen/login` | Identity Verification & Access | Displaced Residents / Requestors |
| **Staff Authentication** | `/auth/login` | Multi-Role Administrative Portal | Gov, Field, & Warehouse Personnel |

---

## 2. Testing Credentials & Simulation Matrix

For sandbox staging, local evaluation, and automated testing, the environment comes pre-configured with the following role accounts.

> 🔑 **Global Verification Password:** `admin1234`
> *(Applies to all pre-seeded testing accounts across all operational domains)*

### 👥 Citizen Directory

Used to simulate aid requests, tracking, and demographic verification.

- 👤 `citizen1` — Primary Sample Resident Profile
- 👤 `citizen2` — Secondary Sample Resident Profile
- 👤 `citizen3` — Tertiary Sample Resident Profile

### 💼 Operational Staff Directory

Used to simulate multi-layered response management, logistics processing, and budget approvals.

```
📁 Staff Testing Matrix
├── 🏛️ Government Branch
│   ├── 👤 gov1 (Executive Officer / Approver)
│   └── 👤 gov2 (Executive Officer / Approver)
│
├── 🦺 Field Operations Unit
│   ├── 👤 field1 (On-Site Intake Specialist)
│   ├── 👤 field2 (On-Site Intake Specialist)
│   └── 👤 field3 (On-Site Intake Specialist)
│
└── 📦 Supply & Logistics Unit
    ├── 👤 wm1 (Regional Warehouse Manager)
    ├── 👤 wm2 (Regional Warehouse Manager)
    └── 👤 wm3 (Regional Warehouse Manager)
```

---

## 3. Specialized Role Workflows & Screen Maps

### 👥 The Citizen Lifecycle

*Empowering individuals through transparency, tracking, and direct access to safety.*

1. **Secure Onboarding (`/citizen/login`):** Enters the citizen portal via validated registration tokens.
2. **Central Control Hub:** Displays active regional shelter directories, localized safe zones, real-time capacities, and the live processing stage of submitted applications.
3. **Profile Auditing:** A critical intake interface where citizens upload essential demographic details required for field team confirmation.
4. **Relocation Request Interface:** A clean, optimized utility built directly into the dashboard enabling citizens to instantly flag emergency situations and request immediate placement.

---

### 🏛️ The Government Command Console

*High-level operational oversight, policy execution, and fiscal governance.*

```
[Gov Console] ──► 📥 Review Shelter Requests ──► [Approve / Route / Deny]
              ──► 💰 Procurement Controls     ──► [Approve Supply Budgets]
              ──► 👥 Regional Management      ──► [Assign Warehouse Chiefs]
```

- **Shelter Request Management:** A central console to verify, grant, or modify crisis shelter placements sent by citizens.
- **Procurement Operations:** Evaluate, authorize, or defer supply requisitions and capital budgets escalated from active field personnel.
- **Personnel Allocations:** Supervise, onboard, and assign regional Warehouse Managers to active logistics facilities.

---

### 🦺 The Field Operations Command

*Tactical field execution, crisis verification, and primary resource tracking.*

- **On-Ground Intake System:** Manually capture and digitize biometric and demographic metadata for victims missing primary network connectivity.
- **Deficit Mitigation Requisitions:** Dynamically generate procurement forms whenever local resource shortages are identified.
- **Asset & Shelter Tasking Engine:** Monitor inventory levels at localized distribution points and track active tasks regarding shelter setup.

---

### 📦 The Warehouse & Logistics Console

*Supply chain integrity, inventory controls, and cross-facility asset routing.*

```
📦 [Warehouse Control Center]
├── 📋 Master Catalog ─── [Item Classifications, Expirations, Batch IDs]
├── 📊 Live Ledger    ─── [Real-Time Stock Quantities, Critical Minimums]
└── 🚚 Route Manager  ─── [Incoming Receipts, Outbound Dispatches, History Log]
```

- **Master Asset Directory:** Maintain a detailed ledger of aid supplies, monitoring asset categories, serial records, and shelf life parameters.
- **Real-Time Stock Manifests:** Visual monitoring tools reflecting instantaneous warehouse quantities and auto-generating re-order warnings.
- **Logistics & Inter-Facility Transfers:** Process incoming shipments, execute distributions, and log complete end-to-end chain of custody asset histories.

---

## 4. End-to-End Operational Workflow

The system synchronizes all four user roles inside a live data pipeline during an emergency deployment cycle:

```
[1] CITIZEN            [2] GOVT OFFICER          [3] FIELD OFFICER         [4] WAREHOUSE MGR
Submit Request  ───►  Evaluate & Approve  ───►  Coordinate Placement ───►  Allocate Supplies
(Identity & Need)     (Authorize Allocation)    (Log Supply Deficits)      (Dispatch Manifest)
```

---

## 5. Local Setup, Initialization, & Deployment

Follow this exact sequence to initialize the development container and run the web platform locally:

1. Launch a shell environment within the project's root folder structure.
2. Spin up the localized web instance using the primary Python wrapper:

   ```bash
   python run.py
   ```

3. Once the logging pipeline confirms successful server initialization, navigate to the local environment endpoint using any standard browser:

   ```
   http://127.0.0.1:5000/
   ```
   ```
   https://sahananeth1.onrender.com/
   ```
   

---

## 6. Telegram Bot Setup (Local & Render)

SAHANANETH sends real-time alerts (approvals, dispatch tasks, low stock, disaster announcements) via a companion Telegram bot, and also lets citizens self-register and request aid directly through it.

### 6.1 Create the bot (one-time)
1. Open Telegram, message **@BotFather**, send `/newbot`, follow the prompts.
2. Copy the token it gives you.
3. Copy `.env.example` to `.env` and fill in:
   ```
   TELEGRAM_BOT_TOKEN=<token from BotFather>
   TELEGRAM_BOT_USERNAME=<your bot's username, no @>
   TELEGRAM_WEBHOOK_SECRET=<any long random string>
   ```

### 6.2 Running locally — polling mode
No public URL needed. In a second terminal, alongside `python run.py`:

```bash
python run_bot_polling.py
```

This continuously checks Telegram for new messages and processes them against your local database. Stop it with `Ctrl+C`; the web app keeps running independently.

### 6.3 Running on Render — webhook mode
Render gives your app a public HTTPS URL, so instead of polling, Telegram pushes updates directly to it — no second process needed.

1. Set the same three environment variables in your Render service's **Environment** tab.
2. After each deploy (or once, if the URL doesn't change), run once from your local machine to point Telegram at your Render URL:
   ```bash
   python scripts/set_webhook.py https://sahananeth1.onrender.com
   ```
3. That's it — the existing web service handles incoming Telegram updates at `/telegram/webhook/<secret>`; you do not need to run `run_bot_polling.py` on Render.

> ⚠️ Don't run polling mode and webhook mode against the same bot token at the same time — Telegram only delivers updates one way at a time. `run_bot_polling.py` automatically clears any existing webhook on startup so local development doesn't get shadowed by a stale Render webhook.

---

*SAHANANETH Operations Manual — Confidential & Operational Framework Documentation.*
