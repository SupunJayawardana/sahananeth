# SAHANANETH User Guide

SAHANANETH is a relief-management system for citizens, government officers, field officers, warehouse managers, and administrators. The main entry page lets users choose between the Citizen portal and the Staff portal.

## 1. Access the system

- Open the landing page at `/`
- Choose one of the two portals:
  - Citizen Login: for residents requesting shelter support
  - Staff Login: for government, field, and warehouse teams

## 2. Sample logins

The sample accounts below are ready for local testing. Use the same password for each sample account:

- Password for all sample accounts: `admin1234`

### Citizen portal
- `citizen1` — sample citizen account
- `citizen2` — sample citizen account
- `citizen3` — sample citizen account

### Staff portal
- `gov1` — government officer
- `gov2` — government officer
- `field1` — field officer
- `field2` — field officer
- `field3` — field officer
- `wm1` — warehouse manager
- `wm2` — warehouse manager
- `wm3` — warehouse manager

## 3. Main workflow screens

### Landing page
- Path: `/`
- Purpose: choose the Citizen or Staff portal

### Citizen workflow
1. Citizen Login
   - Path: `/citizen/login`
   - Use the citizen account to sign in
2. Citizen Dashboard
   - Shows active shelters and request status
3. Citizen Profile
   - Add or update personal details for verification
4. Shelter Request Form
   - Submit a shelter request from the dashboard

### Staff workflow
1. Staff Login
   - Path: `/auth/login`
   - Use a government, field, or warehouse account
2. Staff Dashboard
   - Redirects to the correct dashboard based on role
3. Government Officer Screens
   - Shelter requests
   - Procurement pages
   - Warehouse manager management
4. Field Officer Screens
   - Create procurement records
   - Register citizens
   - Review shelter and inventory tasks
5. Warehouse Manager Screens
   - Catalog view
   - Warehouse stock view
   - Transfer history and warehouse actions

## 4. Typical usage flow

- Citizens log in, complete their profile, and submit shelter requests.
- Government officers review requests and manage procurement needs.
- Field officers handle support tasks and registration work.
- Warehouse managers monitor stock, catalog items, and transfers.

## 5. Running locally

From the project folder, start the application with:

```bash
python run.py
```

Then open the app in your browser at:

```text
http://127.0.0.1:5000/
```
