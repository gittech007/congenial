# RDP Aura Bot — Deployment Guide

Complete step-by-step deployment guide for Ubuntu 24.04 on DigitalOcean.

---

## Prerequisites

- DigitalOcean Droplet with Ubuntu 24.04 (minimum 2 GB RAM / 1 vCPU)
- Domain `panel.rdpaura.me` with DNS A record pointing to the Droplet's IP
  - **Important**: Use DNS-only (gray cloud) in Cloudflare — do NOT proxy through Cloudflare
- SSH access to the Droplet
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Cryptomus API credentials (from [cryptomus.com](https://cryptomus.com))

---

## 1. Install Docker & Docker Compose Plugin

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine and Docker Compose plugin
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to the docker group (optional, avoids sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

---

## 2. Clone Repo and Create Project Directory

```bash
# Clone the repository
git clone https://github.com/gittech007/congenial.git /opt/rdpaura
cd /opt/rdpaura
```

---

## 3. Configure .env File

```bash
# Copy the example env file
cp .env.example .env

# Edit with your actual values
nano .env
```

Fill in **all** values in `.env`:

| Variable | Description |
|---|---|
| `POSTGRES_USER` | Database username (e.g. `rdpaura`) |
| `POSTGRES_PASSWORD` | **Strong** database password |
| `POSTGRES_DB` | Database name (e.g. `rdpaura`) |
| `DATABASE_URL` | Full async connection string (update password to match above) |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook path secret (default: `asdfg`) |
| `TELEGRAM_WEBHOOK_URL` | Full webhook URL (default is correct if using this domain) |
| `CRYPTOMUS_API_KEY` | Your Cryptomus API key |
| `CRYPTOMUS_MERCHANT_ID` | Your Cryptomus merchant ID |
| `ADMIN_USERNAME` | Admin panel login username |
| `ADMIN_PASSWORD` | **Strong** admin panel password |
| `ADMIN_SECRET_KEY` | Random secret for session cookies (generate with `openssl rand -hex 32`) |

**Generate a secure secret key:**
```bash
openssl rand -hex 32
```

---

## 4. Bring Up the Stack

```bash
cd /opt/rdpaura

# Build and start all services in the background
docker compose up -d --build

# Check all services are running
docker compose ps

# View logs
docker compose logs -f app
```

Wait for Caddy to obtain an SSL certificate (usually 10–30 seconds on first start).
Check Caddy logs:
```bash
docker compose logs caddy
```

---

## 5. Run Alembic Migrations

```bash
# Apply all database migrations (creates tables and seeds initial data)
docker compose exec app alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, initial schema and seed data
```

---

## 6. Seed Initial Catalog Data

The Alembic migration (`001_initial.py`) automatically seeds:
- **Countries**: US, UK, AU, CA, GE, IN, SG, NL
- **US States**: New York, San Francisco, Florida, New Jersey
- **Plans**: Basic, Standard, Advanced, Premium, Ultimate, Business
- **OS Options**: Windows 11 Pro, Windows 10 Pro, Windows Server 2019, Windows Server 2022
- **Validity**: 1 Month (30 days)
- **Settings**: `fulfillment_eta`, `support_contact`, `maintenance_mode`
- **Message Templates**: welcome, order_summary, payment_created, processing, completed, manual_review, cancelled

No additional seeding is required.

To verify the seed data:
```bash
docker compose exec postgres psql -U rdpaura -d rdpaura -c "SELECT name, prefix FROM countries;"
docker compose exec postgres psql -U rdpaura -d rdpaura -c "SELECT name, price_usd FROM plans ORDER BY sort_order;"
```

---

## 7. Set Telegram Webhook URL

The webhook is automatically set when the `app` service starts (via the lifespan handler).

To verify or manually re-set it:
```bash
# Verify current webhook
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo" | python3 -m json.tool

# Manually set webhook (replace YOUR_BOT_TOKEN)
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://panel.rdpaura.me/telegram/webhook/asdfg", "drop_pending_updates": true}'
```

---

## 8. Verify Everything Works

### Check application health:
```bash
curl https://panel.rdpaura.me/health
# Expected: {"status":"ok"}
```

### Check admin panel:
Open `https://panel.rdpaura.me/admin` in your browser.
- Login with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from your `.env`

### Check SSL certificate:
```bash
curl -I https://panel.rdpaura.me
# Should show HTTP/2 200
```

### Check running containers:
```bash
docker compose ps
# All three services (postgres, app, caddy) should be "running"
```

### View application logs:
```bash
docker compose logs -f app      # App logs
docker compose logs -f caddy    # Caddy/SSL logs
docker compose logs -f postgres # Database logs
```

---

## 9. Testing Checklist (End-to-End)

### ✅ Infrastructure
- [ ] All 3 Docker containers running (`docker compose ps`)
- [ ] HTTPS working: `curl -I https://panel.rdpaura.me` returns 200
- [ ] Health endpoint responding: `curl https://panel.rdpaura.me/health`
- [ ] Database migrations applied: check with `docker compose exec postgres psql -U rdpaura -d rdpaura -c "\dt"`

### ✅ Admin Panel
- [ ] `https://panel.rdpaura.me/admin` loads the login page
- [ ] Login works with credentials from `.env`
- [ ] Can see Countries, Plans, OS Options, etc. under **Catalog** menu
- [ ] Can edit Settings (fulfillment_eta, support_contact)
- [ ] Can edit Message Templates

### ✅ Telegram Bot
- [ ] Bot responds to `/start` with welcome message and "🛒 New Order" button
- [ ] Country selection shows 8 country buttons (US, UK, AU, CA, GE, IN, SG, NL)
- [ ] Selecting US shows state selection (New York, San Francisco, Florida, New Jersey)
- [ ] Selecting non-US country skips state selection
- [ ] Plan selection shows 6 plans with correct format (PREFIX-Name / RAM | CPU | SSD / Price)
- [ ] OS selection shows 4 Windows options
- [ ] Validity selection shows "1 Month"
- [ ] Email prompt appears after validity; validates email format
- [ ] Invalid email triggers re-prompt
- [ ] ⬅️ Back buttons work at each step
- [ ] Back from Email → Validity
- [ ] Changing Country clears all downstream selections

### ✅ Payment Flow
- [ ] After valid email, order summary + "💳 Pay Now" URL button appears
- [ ] "💳 Pay Now" button links to Cryptomus payment page
- [ ] "I Paid ✅" button works (shows appropriate status message)
- [ ] Once invoice exists, Back button is replaced by "🏠 Main Menu"

### ✅ Cryptomus Webhook
- [ ] POST to `https://panel.rdpaura.me/payments/cryptomus/webhook` returns 200
- [ ] Invalid signature returns 401
- [ ] Non-final webhooks return 200 without state changes
- [ ] `paid` status with valid signature updates order to `processing`
- [ ] `paid` status after expiry sets order to `manual_review`
- [ ] `wrong_amount` sets order to `manual_review`
- [ ] Webhook events logged to `webhook_events` table

### ✅ Payment Expiry (2-hour limit)
- [ ] Scheduler runs every 60 seconds (check logs: `docker compose logs -f app | grep scheduler`)
- [ ] After 2 hours, unpaid orders auto-expire (status: `cancelled_expired`)
- [ ] No Telegram notification sent when order auto-expires

### ✅ Admin Actions
- [ ] **Approve Late Payment**: manual_review → processing; Telegram message sent
- [ ] **Reject Late Payment**: manual_review → cancelled_expired; notification sent
- [ ] **Mark Completed + Send Delivery**: Opens form for IP/User/Pass/Expiry; sends delivery message; order → completed
- [ ] **Resend Delivery**: Resends delivery credentials for completed order

---

## Troubleshooting

### Bot not responding
```bash
# Check webhook status
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Check app logs for errors
docker compose logs app | grep ERROR
```

### SSL certificate not working
```bash
# Check Caddy logs
docker compose logs caddy

# Ensure ports 80 and 443 are open
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status
```

### Database connection errors
```bash
# Check postgres is healthy
docker compose exec postgres pg_isready -U rdpaura

# Check DATABASE_URL in .env matches POSTGRES_* vars
```

### Restart services
```bash
docker compose restart app     # Restart only the app
docker compose down && docker compose up -d  # Full restart
```

### Update application
```bash
cd /opt/rdpaura
git pull
docker compose up -d --build
docker compose exec app alembic upgrade head
```
