# Flutter Login / Attendance API — Postman Testing Guide

Covers every route exposed by `addons/flutterlogin` and `addons/flutterattendance`.
A ready-to-import collection is at `Flutter_API.postman_collection.json` (same folder as this file) —
import it and you only need to set `base_url` and login once; the token is captured automatically.

## Global setup

| Postman variable | Example value |
|---|---|
| `base_url` | `http://localhost:8069` (or your VPS URL) |
| `token` | auto-filled by the login request's Test script |

**Auth model**: every route except `/api/login` and `/api/forgot-password` requires
`Authorization: Bearer <token>` (a JWT, 24h expiry). All bodies are raw JSON
(`Content-Type: application/json`), all requests are `type=http` (not JSON-RPC), CSRF is disabled, CORS is `*`.

All responses are JSON with `"success": true|false`. Errors look like:
```json
{ "success": false, "error": "message here" }
```

---

## flutterlogin

### POST `/api/login`
Auth: **public**

Headers: `Content-Type: application/json`

Body:
```json
{
  "email": "admin@yourcompany.com",
  "password": "admin",
  "device_id": "test-device-001",
  "device_name": "Postman",
  "os_version": "N/A",
  "app_version": "1.0"
}
```
- `email` can also be an employee ID / barcode (or send `login` instead of `email`) — the controller resolves it to a user login.
- `device_id` etc. are optional. If omitted, device-binding is skipped entirely. If sent, the employee is locked to one active device at a time — logging in from a second `device_id` while another is `active` returns `403` until an admin approves it (via the Device model in Odoo backend).

Response `200`:
```json
{
  "success": true,
  "token": "eyJhbGciOi...",
  "expires_in": 86400,
  "employee_id": 5,
  "employee_name": "Mitchell Admin",
  "company": "My Company",
  "department": "Management",
  "job_position": "Manager",
  "work_email": "admin@yourcompany.com"
}
```
Errors: `400` missing fields, `401` invalid credentials, `403` no employee record / employee inactive / mobile access disabled / device conflict.

**Postman tip**: add this Test script so every later request reuses the token:
```js
if (pm.response.code === 200) {
    const json = pm.response.json();
    if (json.token) pm.collectionVariables.set("token", json.token);
}
```

### GET `/api/profile`
Auth: **Bearer token**. No body.

Response `200`:
```json
{
  "success": true,
  "employee_id": 5,
  "employee_name": "Mitchell Admin",
  "company": "My Company",
  "department": "Management",
  "job_position": "Manager",
  "work_email": "admin@yourcompany.com"
}
```

### POST `/api/logout`
Auth: **Bearer token**. No body. Revokes the current token's `jti`.

Response `200`: `{"success": true, "message": "Logged out"}`

### POST `/api/refresh`
Auth: **Bearer token**. No body. Issues a new token and revokes the old one — **update your `token` variable with the new value** in the Test script (same snippet as login).

Response `200`: `{"success": true, "token": "...", "expires_in": 86400}`

### POST `/api/forgot-password`
Auth: **public**.

Body:
```json
{ "email": "admin@yourcompany.com" }
```
Response `200` (always, regardless of whether the account exists):
```json
{ "success": true, "message": "If an account exists for this email, a password reset link has been sent." }
```

---

## flutterattendance

All routes below require header `Authorization: Bearer {{token}}`.

### POST `/api/check-in`
Body:
```json
{
  "latitude": 25.276987,
  "longitude": 55.296249,
  "address": "Office HQ",
  "accuracy": 10.5,
  "battery": 87.0,
  "network": "wifi",
  "internet": true,
  "photo": "<base64 jpeg, optional, may include data:image/jpeg;base64, prefix>",
  "device_id": "test-device-001",
  "device_name": "Postman",
  "os_version": "N/A",
  "app_version": "1.0"
}
```
- `latitude`/`longitude` required, else `400`.
- If office GPS + radius are configured (`ir.config_parameter`: `flutterattendance.office_latitude/longitude/gps_radius_meters`), being outside the radius returns `403`.
- Already has an open session → `409`.

Response `200`: full attendance record (see shape under `/api/today` below).

### POST `/api/check-out`
Same body shape as check-in (latitude/longitude required). Fails `409` if there's no open session to close.

### GET `/api/today`
No body/query. Returns today's records for the authenticated employee:
```json
{
  "success": true,
  "records": [ { "id": 12, "attendance_date": "2026-08-02", "check_in_time": "...", "check_out_time": false,
                 "working_hours": 0.0, "distance_km": 0.0, "late_minutes": 0.0, "overtime_hours": 0.0,
                 "status": "present", "remarks": false,
                 "checkin": { "latitude": 25.27, "longitude": 55.29, "address": "Office HQ", "accuracy": 10.5,
                              "has_photo": false, "photo_url": false, "battery": 87.0, "network": "wifi",
                              "internet": true, "ip_address": "1.2.3.4", "created_at": "..." },
                 "checkout": { "latitude": false, "longitude": false, "address": false, "accuracy": false,
                               "has_photo": false, "photo_url": false, "created_at": false },
                 "device": "Postman" } ],
  "is_checked_in": true,
  "last_check_in": "2026-08-02T08:00:00",
  "last_check_out": false
}
```

### GET `/api/history`
Query params (all optional): `date_from`, `date_to` (YYYY-MM-DD), `limit` (default 30), `offset` (default 0).
Example: `{{base_url}}/api/history?date_from=2026-07-01&date_to=2026-08-02&limit=10&offset=0`

Response: `{"success": true, "total": 42, "records": [ ...same shape as above... ]}`

### GET `/api/history/{att_id}`
Path param `att_id`. `404` if not found or not owned by the caller.
Response: `{"success": true, ...attendance record...}`

### PUT `/api/history/{att_id}`
Body (owner can only send `remarks`; HR group `hr.group_hr_user` can also send `check_in_time`, `check_out_time`, `status`):
```json
{
  "remarks": "Forgot to check out on time",
  "check_in_time": "2026-08-02 08:00:00",
  "check_out_time": "2026-08-02 17:00:00",
  "status": "present"
}
```
`status` must be one of `present`, `late`, `half_day`. `403` if not owner and not HR. `400` if no editable fields given.

### DELETE `/api/history/{att_id}`
HR only (`403` otherwise). No body. Response: `{"success": true, "message": "Attendance record deleted"}`

### GET `/api/attendance/{att_id}/photo/{which}`
Path params: `att_id`, `which` = `checkin` or `checkout`. No body.
Returns raw `image/jpeg` bytes (not JSON) — in Postman, check the **Body → Preview** tab to view it. `404` if no photo or not authorized.

### GET `/api/dashboard`
No body/query. Response:
```json
{
  "success": true,
  "is_checked_in": true,
  "last_check_in": "2026-08-02T08:00:00",
  "last_check_out": false,
  "working_hours_today": 3.5,
  "late_by_minutes": 0.0,
  "overtime_hours": 0.0,
  "today_status": "present",
  "shift": { "name": "General", "start_time": 9.0, "end_time": 18.0, "break_start_time": 13.0,
             "break_minutes": 60, "grace_minutes": 10, "half_day_hours": 4.0, "full_day_hours": 8.0,
             "working_days": { "monday": true, "tuesday": true, "wednesday": true, "thursday": true,
                                "friday": true, "saturday": false, "sunday": false } },
  "month": { "days_present": 15, "total_working_days": 22, "attendance_percentage": 68.2, "avg_work_per_day": 7.9 }
}
```

### GET `/api/notifications`
Query param (optional): `unread_only=true`.
Response: `{"success": true, "unread_count": 2, "notifications": [ {"id":1, "type": "...", "title": "...", "body": "...", "for_date": "2026-08-02", "is_read": false, "created_at": "..."} ]}`

### POST `/api/notifications/{notif_id}/read`
No body. Marks it read for the authenticated employee. `404` if not found/not owned.

### PUT `/api/profile`
Only `mobile_phone` and `work_phone` are editable here (name/dept/job are HR-managed).
Body:
```json
{ "mobile_phone": "+971500000000", "work_phone": "+97140000000" }
```
`400` if neither field is present.

### POST `/api/profile/photo`
Body:
```json
{ "photo": "<base64 jpeg/png, optional data:...;base64, prefix>" }
```
`400` if missing or not a valid image. Response: `{"success": true, "message": "Profile photo updated"}`

### GET `/api/settings`
No body/query. Response:
```json
{
  "success": true,
  "gps_radius_meters": 200,
  "company_name": "My Company",
  "attendance_rules": { "shift_name": "General", "start_time": 9.0, "end_time": 18.0,
                        "grace_minutes": 10, "half_day_hours": 4.0, "full_day_hours": 8.0 },
  "theme": "default",
  "language": "en_US"
}
```

### POST `/api/sync`
Batch upload of offline-queued check-in/check-out actions, applied in array order.

Body:
```json
{
  "items": [
    {
      "client_uuid": "uuid-1",
      "action": "check_in",
      "timestamp": "2026-08-02 08:00:00",
      "latitude": 25.276987,
      "longitude": 55.296249,
      "address": "Office HQ",
      "accuracy": 10.5,
      "photo": null,
      "device_id": "test-device-001",
      "device_name": "Postman",
      "os_version": "N/A",
      "app_version": "1.0",
      "battery": 87.0,
      "network": "wifi",
      "internet": true
    },
    {
      "client_uuid": "uuid-2",
      "action": "check_out",
      "timestamp": "2026-08-02 17:00:00",
      "latitude": 25.276987,
      "longitude": 55.296249
    }
  ]
}
```
Response `200` (always 200 — per-item failures are reported inside `results`):
```json
{
  "success": true,
  "results": [
    { "client_uuid": "uuid-1", "success": true, "attendance_id": 12 },
    { "client_uuid": "uuid-2", "success": true, "attendance_id": 12 }
  ]
}
```

---

## Quick smoke-test order in Postman
1. `POST /api/login` → captures `{{token}}`.
2. `GET /api/profile` → confirm the Bearer header works.
3. `POST /api/check-in` → then `GET /api/today` → then `POST /api/check-out`.
4. `GET /api/dashboard`, `GET /api/settings`, `GET /api/history`.
5. `POST /api/logout` → then retry `GET /api/profile` and confirm it now returns `401 Token has been revoked`.
