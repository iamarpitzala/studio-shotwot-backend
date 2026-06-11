# ShotWot API Endpoints Integration & cURL Testing Guide

Below are the cURL commands for all 7 endpoints to test and verify integration with your frontend.

---

### Prerequisites
1. **Mock Token / Real Firebase ID Token**: 
   Since all protected routes decode and verify tokens via `firebase_admin.auth.verify_id_token`, you must pass a valid Firebase JWT ID Token in the `Authorization` header.
   ```bash
   export ID_TOKEN="YOUR_FIREBASE_ID_TOKEN"
   export API_URL="http://localhost:8000"
   ```

---

### 1. User Registration (`POST /auth/register`)
Called immediately by the frontend after a user registers via the Firebase Client SDK.

```bash
curl -X POST "$API_URL/auth/register" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "companyName": "Acme Corp",
    "industry": "Technology",
    "companySize": "50-200"
  }'
```

---

### 2. Fetch User Profile & Usage Stats (`GET /users/me`)
Retrieves the user's plan details and generation quota usage.

```bash
curl -X GET "$API_URL/users/me" \
  -H "Authorization: Bearer $ID_TOKEN"
```

---

### 3. Upload Reference Asset (`POST /vault/upload`)
Uploads a brand asset (JPG/PNG/WebP) to the private GCS Vault.

```bash
curl -X POST "$API_URL/vault/upload" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -F "file=@/path/to/your/reference_image.jpg" \
  -F "category=person"
```
*Response returns the `assetId` needed for generation.*

---

### 4. List Vault Assets (`GET /vault/assets`)
Returns all reference assets with short-lived GCS signed URLs.

```bash
curl -X GET "$API_URL/vault/assets" \
  -H "Authorization: Bearer $ID_TOKEN"
```

---

### 5. Delete Vault Asset (`DELETE /vault/assets/:assetId`)
Removes an asset from GCS and Firestore.

```bash
curl -X DELETE "$API_URL/vault/assets/your-asset-uuid-here" \
  -H "Authorization: Bearer $ID_TOKEN"
```

---

### 6. Submit Generation Job (`POST /generate`)
Kicks off the non-blocking background pipeline.

```bash
curl -X POST "$API_URL/generate" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "brief": "Our CEO presenting at a Mumbai tech conference, professional LinkedIn banner, confident and warm",
    "referenceAssetId": "your-asset-uuid-here",
    "aspectRatio": "1:1"
  }'
```
*Response returns the `generationId` for polling.*

---

### 7. Poll Generation Status (`GET /generate/:generationId`)
Poll status (`pending` -> `processing` -> `complete` / `failed`). Once complete, returns the optimized prompt and the 24h signed output URL.

```bash
curl -X GET "$API_URL/generate/your-generation-uuid-here" \
  -H "Authorization: Bearer $ID_TOKEN"
```

---

### 8. Fetch Generation History (`GET /generate/history`)
Retrieves the last 20 generation records for the user.

```bash
curl -X GET "$API_URL/generate/history" \
  -H "Authorization: Bearer $ID_TOKEN"
```
