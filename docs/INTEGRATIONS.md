# Connecting outside services

Every connection is optional. Without a key the feature is hidden or reports "not set up", and the rest of the app keeps working. Keys go into the `.env` file next to `docker-compose.yml` (or `backend/.env` without Docker). After changing `.env`:

```bash
docker compose up -d
```

**Admin → Settings → Connections** shows which ones the server sees. A value in `.env` is shown as **Not tested**. Press **Test** (or **Test all**) after every change: the server sends one harmless request to the service and shows **Working**, or **Problem** with the reason (wrong key, retired model, missing setting, service not reachable). A test charges nothing, creates nothing at the provider and sends no e-mail. The assistant test asks the model for one word.

| Service | Used for | Cost | Settings |
|---|---|---|---|
| Google sign-in | "Continue with Google" | Free | `GOOGLE_CLIENT_ID` |
| Google Gemini | Assistant answers, daily post text | Free tier, then paid | `LLM_ENABLED`, `GEMINI_API_KEY` |
| Image model | Illustrations in the assistant | Paid per image | `LLM_IMAGE_ENABLED` |
| Stripe | Card payments | No monthly fee, a fee per payment | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| PayPal | PayPal payments | No monthly fee, a fee per payment | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE` |
| E-mail (SMTP) | Password reset, appointment reminders | Free with Gmail | `SMTP_*` |
| n8n | Automation workflows | Free when self-hosted | API key and webhook made in the admin panel |
| Zapier | Automation workflows | Webhooks need a paid plan | API key and webhook made in the admin panel |

Never put a key into the code, a screenshot or a chat. If a key leaks, delete it at the provider and make a new one.

## 1. Sign in with Google

1. Open https://console.cloud.google.com, create a project, then **APIs & Services → OAuth consent screen**. Choose *External*, enter the app name and your e-mail, and publish the app.
2. **APIs & Services → Credentials → Create credentials → OAuth client ID**, type **Web application**.
3. Under **Authorised JavaScript origins** add every address the app is opened from, for example `http://localhost:5173` and `https://your-site-domain`. No redirect URI is needed.
4. Copy the **Client ID** (it ends in `.apps.googleusercontent.com`) into `.env`:

```env
GOOGLE_CLIENT_ID=1234567890-abc.apps.googleusercontent.com
```

How it is checked: the browser gets a signed ID token from Google and sends it to `POST /auth/google`. The server verifies the signature against Google's public keys, the audience (your client ID), the issuer, the expiry and that the e-mail is verified. An existing account with the same address is linked. If that account never proved its address, its old password is discarded.

## 2. Gemini for the assistant

1. Open https://aistudio.google.com/apikey and create an API key.
2. In `.env`:

```env
LLM_ENABLED=true
GEMINI_API_KEY=your-key
```

Without it the assistant answers from built-in rules (still with tables for routines). With it, it answers freely in English, Urdu or Roman Urdu.

**Model names change.** Google retires Gemini models every few months. When the model in `GEMINI_MODEL` no longer exists for your key, the server reads the list of models the key may use, switches to the newest "flash" model and writes that to the log. The connection test names the model in use, so you can put it into `GEMINI_MODEL`. If the test reports that the quota is used up, wait a minute or choose another model.

`LLM_MAX_OUTPUT_TOKENS` (default 1500) is the wanted size of one answer. Newer models think before they answer and that thinking counts against the limit, so the server adds an allowance on top; a small value no longer cuts answers in the middle.

**Illustrations** ("make an image of a morning routine") need an image model and are billed per image. Turn them on with `LLM_IMAGE_ENABLED=true`. The model names are in `GEMINI_IMAGE_MODEL` / `OPENAI_IMAGE_MODEL`. Because images cost money, an image model is never replaced automatically: when one is retired, the connection test lists the image models your key can use. Each user can make `CHAT_IMAGES_PER_DAY` images (default 10).

Voice input and read-aloud need no key: they use the browser (Chrome and Edge support Urdu speech recognition; Firefox has no speech recognition).

## 3. Card payments with Stripe

The customer pays on Stripe's page. Card numbers never reach Skyntri.

1. Create an account at https://dashboard.stripe.com. **Check first that Stripe supports businesses in your country**: it has not supported Pakistan-registered businesses. Test mode works for a demo in any case.
2. **Developers → API keys**: copy the **Secret key**. `sk_test_...` takes no real money; `sk_live_...` does.
3. **Developers → Webhooks → Add endpoint**:
   * URL: `https://YOUR_API_DOMAIN/payments/stripe/webhook`
   * Event: `checkout.session.completed`
   * Copy the **Signing secret** (`whsec_...`).
4. In `.env`:

```env
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

Test card: `4242 4242 4242 4242`, any future date, any CVC.

Without the webhook secret, a payment is confirmed only when the customer returns to the site after paying. With it, Stripe also tells the server directly, which covers a closed browser tab.

## 4. PayPal

1. Open https://developer.paypal.com → **Apps & Credentials**. **Check that PayPal offers business accounts in your country**: it has not been available in Pakistan.
2. Create an app. Copy the **Client ID** and **Secret** of the *Sandbox* tab for testing, or of the *Live* tab for real payments.
3. In `.env`:

```env
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
PAYPAL_MODE=sandbox
```

PayPal cannot charge Pakistani rupees. Prices are converted with a rate you set:

```env
PAYPAL_CURRENCY=USD
PAYPAL_EXCHANGE_RATE=280
```

`280` means 280 PKR = 1 USD. The button then shows the USD amount before the customer leaves the site. Update the rate when it changes. With rate `0`, PayPal stays off while the shop currency is PKR.

**Local gateways.** Safepay, PayFast, JazzCash or Easypaisa can be added as another provider in `backend/app/services/payments.py`: create a checkout, send the browser there, then ask the provider whether it was paid.

**Refunds** are made in the Stripe or PayPal dashboard. Afterwards mark the order or appointment as refunded in the admin panel.

## 5. E-mail (password reset and reminders)

With Gmail: turn on 2-step verification, then create an **App password** at https://myaccount.google.com/apppasswords.

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=the-16-letter-app-password
SMTP_FROM=you@gmail.com
```

## 6. Agents and automation

### Built-in agents

| Agent | What it does |
|---|---|
| `daily_report` | Yesterday in numbers: new patients, analyses, appointments, orders, online payments, most common skin concerns |
| `appointment_reminders` | Reminds patients of confirmed appointments in the next 24 hours (e-mail when SMTP is set up, plus an event for WhatsApp/SMS workflows) |
| `daily_post` | Writes a short skin-care post about what patients asked about most this week. Saved as a draft unless **Admin → Settings → Publish daily posts automatically** is on |

The agents use totals only. They never read photos, visit reasons, assessments or prescriptions.

Three ways to run them:
* **Admin → Automation → Agents → Run now.**
* **By the server:** set `AGENTS_SCHEDULER_ENABLED=true`. Reminders run every hour, the report and the post once a day at `AGENT_DAILY_HOUR` (clinic time zone).
* **By n8n / Zapier / cron:** call the API (below). Leave the server scheduler off in that case.

### Events Skyntri sends (webhooks)

Add the receiving address under **Admin → Automation → Webhooks**.

| Event | When |
|---|---|
| `appointment.created` | A patient booked |
| `appointment.updated` | Confirmed, completed or cancelled |
| `appointment.reminder` | The reminder agent found an appointment in the next 24 hours |
| `payment.succeeded` | An online payment was received |
| `order.created` | A shop order was placed |
| `doctor.applied` | A doctor applied and waits for approval |
| `post.published` | A clinic post was published (title and text included) |
| `report.daily` | The daily report is ready |

Each request is a JSON body `{"id", "event", "created_at", "data"}` with these headers:

```
X-Skyntri-Event: appointment.created
X-Skyntri-Timestamp: 1794000000
X-Skyntri-Signature: sha256=<HMAC-SHA256 of "<timestamp>.<raw body>" with the webhook's signing secret>
```

Check the signature and refuse messages older than five minutes. The signing secret is shown when you open the webhook in the admin panel.

**Privacy.** Events carry ids, times and status. The reason for a visit, assessments and prescriptions are never sent. The patient's name, e-mail and phone are sent only to a webhook where *Include contact details* is switched on. Do that only for a service you trust and have a data-processing agreement with.

In production, webhook addresses must be `https://` and public. To call a private host such as the n8n container, list it in `AUTOMATION_ALLOWED_HOSTS` (the Compose files already allow `n8n`).

### API for automation tools

Create a key under **Admin → Automation → API keys**. It is shown once. Send it as `X-API-Key`.

| Call | Scope | Result |
|---|---|---|
| `GET /automation/v1/summary/daily` | `read:summary` | The last daily report |
| `GET /automation/v1/appointments?hours_ahead=24&status=confirmed` | `read:appointments` | Upcoming appointments with contact details |
| `POST /automation/v1/appointments/{id}/status` `{"status": "confirmed"}` | `write:appointments` | Confirm or cancel |
| `POST /automation/v1/posts` `{"title", "body", "kind", "publish"}` | `write:posts` | Create a clinic post |
| `POST /automation/v1/agents/{name}/run?once_per=day` | `run:agents` | Start an agent; `once_per=hour|day` makes repeated calls harmless |

```bash
curl -X POST "http://localhost:8000/automation/v1/agents/daily_report/run?once_per=day" -H "X-API-Key: sky_..."
```

Give each tool its own key with only the scopes it needs, and revoke a key you no longer use.

### n8n (free, runs next to Skyntri)

```bash
docker compose --profile automation up -d
```

Open http://localhost:5678 and create the n8n owner account. Two ready workflows are in `automation/n8n/`. Import each with **Workflows → Import from file**.

**`skyntri-daily-agents.json`: n8n starts the agents.**
1. In Skyntri create an API key with the scope `run:agents`.
2. In the node *Settings (API address and key)* paste the key. The address `http://backend:8000` is right for Docker Compose.
3. Click **Execute workflow** to test, then switch the workflow to **Active**.

**`skyntri-events.json`: n8n receives events.**
1. In Skyntri add a webhook with the URL `http://n8n:5678/webhook/skyntri`. Turn on *Include contact details* if n8n should send reminders.
2. Open the webhook in Skyntri, copy the **Signing secret** and paste it into the *Check signature* node (`PASTE_SIGNING_SECRET_HERE`).
3. Switch the workflow to **Active**, then press **Send test event** in Skyntri.
4. After each *… text* node, add the node that sends the message: WhatsApp Business Cloud, Twilio, Telegram, Gmail, Facebook Pages, Slack … n8n asks for that service's own login.

Both workflows were imported and run in n8n 2.47.4 against a running Skyntri: the agents started with the API key, signed events were accepted, and a wrong secret or an old timestamp was refused.

On a server, n8n listens only on the server itself. Reach it with an SSH tunnel:

```bash
ssh -L 5678:localhost:5678 root@YOUR_SERVER_IP
```

Posting to Facebook, Instagram or WhatsApp needs those platforms' business accounts and approvals; n8n's node documentation lists the steps.

### Zapier, Make and others

* **Receive events:** create a Zap with the trigger *Webhooks by Zapier → Catch Hook* (needs a paid Zapier plan), and paste its URL as a webhook in Skyntri. Zapier cannot easily check the signature, so do not switch on contact details for it unless you accept that.
* **Call Skyntri:** use the action *Webhooks by Zapier → Custom Request* with the `X-API-Key` header and the calls from the table above. Skyntri must be reachable from the internet (a deployed server, not `localhost`).
* **Your own agent** (LangChain, CrewAI, a script …) uses the same API and the same webhooks.
