# Firebase Cloud Messaging (FCM) Setup for Farmer Push Notifications

This guide explains how to set up Firebase Cloud Messaging for sending push notifications to farmers.

## Prerequisites

1. A Firebase project (create one at https://console.firebase.google.com/)
2. Service account credentials from Firebase

## Setup Steps

### 1. Create Firebase Project

1. Go to https://console.firebase.google.com/
2. Click "Add project" and follow the setup wizard
3. Once created, go to Project Settings > Service Accounts
4. Click "Generate new private key"
5. Save the JSON file securely

### 2. Configure Django Backend

Add the following to your `settings.py`:

```python
# Firebase Configuration
FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'path', 'to', 'firebase-credentials.json')
# OR embed the credentials directly (for Docker/containers)
# FIREBASE_CREDENTIALS = json.loads(os.environ.get('FIREBASE_CREDENTIALS_JSON', '{}'))
```

For environment variable approach (recommended for production):

```bash
export FIREBASE_CREDENTIALS_JSON='{"type": "service_account", ...}'
```

### 3. Install firebase-admin

```bash
pip install firebase-admin
```

### 4. Test the Setup

Use the management command to test notifications:

```bash
# First, get a farmer's ID and ensure they have an FCM token
python manage.py shell -c "from apps.accounts.models import FarmerProfile; print([(f.id, f.user.username, f.fcm_token[:20] if f.fcm_token else 'No token') for f in FarmerProfile.objects.all()])"

# Send a test notification
python manage.py test_farmer_notification <farmer_id> --title "Test" --body "Hello from FreshOn!"
```

## How It Works

### Token Registration Flow

1. Farmer opens the Farm_app
2. App requests notification permission
3. If granted, Firebase generates an FCM token
4. App sends token to backend via `PATCH /api/farmer/profile/` with `{fcm_token: "..."}`
5. Backend stores token in `FarmerProfile.fcm_token`

### Sending Notifications

The backend can send notifications using helper functions:

```python
from apps.farmer.notifications import notify_new_order, notify_payment_credited

# When a new order comes in
notify_new_order(farmer_profile, order_id="ORD-123", product_name="Tomatoes", quantity="5 kg")

# When payment is credited
notify_payment_credited(farmer_profile, amount="1500.00", payout_id="PAY-456")
```

### Notification Types

| Type | Trigger | Payload |
|------|---------|---------|
| `new_order` | Order placed for farmer's product | `{order_id, product_name, quantity}` |
| `payment_credited` | Payout completed | `{amount, payout_id}` |
| `pickup_scheduled` | Pickup requested | `{order_id, pickup_time}` |
| `quality_alert` | Quality issue reported | `{message}` |

## Troubleshooting

### "Farmer has no FCM token registered"

- Farmer hasn't enabled push notifications in the app
- Ask them to go to their profile and enable notifications

### "Failed to send notification"

- Check Firebase credentials are correctly configured
- Verify `firebase-admin` is installed
- Check Django logs for detailed error messages

### Token Invalid Errors

If a token becomes invalid (app uninstalled, etc.), the system automatically clears it from the database on the next send attempt.

## Security Considerations

- FCM tokens are user-specific and should be treated as sensitive data
- Tokens are stored in plain text (required by FCM) but should be protected via database security
- Always use HTTPS for communication between app and backend
- Rotate Firebase service account keys periodically
