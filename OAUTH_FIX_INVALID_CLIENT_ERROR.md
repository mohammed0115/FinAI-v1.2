# 🔧 Fix OAuth Client Invalid Error (invalid_client:401)

## Problem
Google OAuth returns: `The OAuth client was not found` with error `invalid_client:401`

## Solution: Add Redirect URIs to Google Cloud Console

### Step 1: Go to Google Cloud Console
1. Open: https://console.cloud.google.com/
2. Make sure you're logged in with the same Google account that owns the OAuth app

### Step 2: Select Your Project
1. Click on the project dropdown (top left, near "Google Cloud")
2. Find and select your project (likely something like "FinAI" or similar)

### Step 3: Navigate to OAuth Credentials
1. In left sidebar: **APIs & Services** → **Credentials**
2. You should see your OAuth 2.0 Client ID listed
3. Click on it to open the details

### Step 4: Add All Redirect URIs
In the **"Authorized redirect URIs"** section, add ALL of these:

```
http://localhost:8000/auth/google/callback/
http://127.0.0.1:8000/auth/google/callback/
https://localhost:8000/auth/google/callback/
https://127.0.0.1:8000/auth/google/callback/
```

If you have a real domain (like tadgeeg.com), also add:
```
https://tadgeeg.com/auth/google/callback/
https://www.tadgeeg.com/auth/google/callback/
```

### Step 5: Save Changes
1. Click **"Save"** button at the bottom
2. Close the dialog

### Step 6: Restart Django Server
```bash
# Stop the running server (Ctrl+C in terminal)
# Then restart:
cd /home/mohamed/FinAI-v1.2/backend
source venv/bin/activate
python manage.py runserver
```

### Step 7: Clear Browser Cache
1. Open Browser DevTools (F12)
2. Right-click refresh button → "Empty Cache and Hard Refresh"
3. Or: Close all Google login tabs and try again

### Step 8: Test Again
1. Go to http://localhost:8000/login/
2. Click "Continue with Google"
3. Should now work!

---

## Additional Checks

### Check 1: Verify OAuth Consent Screen is Configured
1. In Google Cloud Console: **APIs & Services** → **OAuth consent screen**
2. Make sure "External" is selected
3. App name should be filled in
4. Your email should have at least "Editor" access

### Check 2: Enable Google+ API
1. **APIs & Services** → **Library**
2. Search for "Google+ API"
3. Click **"Enable"** if not already enabled

### Check 3: Check Error Logs
```bash
# Check Django server output for detailed errors:
# If you see "Redirect URI mismatch", that confirms this issue
```

---

## Common Redirect URI Issues

| Issue | Solution |
|-------|----------|
| `http` vs `https` | Must match exactly |
| `localhost` vs `127.0.0.1` | Add both versions |
| Trailing slash | Make sure all have `/` at end |
| Port number | Must include `:8000` for dev |
| Domain vs localhost | Must match your actual access URL |

---

## If Still Not Working

1. **Clear .env cache:**
   ```bash
   cd /home/mohamed/FinAI-v1.2/backend
   source venv/bin/activate
   python -c "from django.conf import settings; print(f'Client ID: {settings.GOOGLE_CLIENT_ID}')"
   ```

2. **Check Django settings:**
   The output should show your client ID (starting with numbers like `527140788392-`)

3. **Check network requests:**
   - Open Firefox DevTools (F12)
   - Go to Network tab
   - Click "Continue with Google"
   - Look for the `oauth2/v2/auth` request
   - Check the `redirect_uri` parameter

4. **Try different browser:**
   - Clear all cookies for accounts.google.com
   - Try Incognito/Private window
   - Try different browser

---

## Quick Copy-Paste Redirect URIs

Simply copy-paste these into Google Cloud Console "Authorized redirect URIs":

```
http://localhost:8000/auth/google/callback/
http://127.0.0.1:8000/auth/google/callback/
```

Then click Save and test!
