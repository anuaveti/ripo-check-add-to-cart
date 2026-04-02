# Insectnets Cart Monitor

This project automatically tests the add‑to‑cart functionality of [insectnets.com](https://insectnets.com) every hour using **Selenium** in headless Chrome. It runs on **GitHub Actions** (free) and sends email notifications with a cart screenshot when the test passes, or an error report when it fails.

## Overview

- **Test script** (`monitor.py`):  
  - Opens the homepage, dismisses pop‑ups.  
  - Navigates to the windows category (first menu item, skipping “Home”).  
  - Adds three window products to the cart (second, first, and third in the grid).  
  - Navigates to the doors category (second menu item or link containing “durv”).  
  - Adds two door products to the cart (first and fifth in the grid).  
  - Goes to the cart page and takes a screenshot.  
  - Sends an email with the result (and screenshot on success).

- **GitHub Actions workflow** (`.github/workflows/hourly.yml`):  
  - Runs every hour on the hour (`cron: '0 * * * *'`).  
  - Can also be triggered manually from the Actions tab.  
  - Installs Chrome, ChromeDriver, Python dependencies, and executes `monitor.py`.  
  - Uses repository secrets to keep credentials safe.

- **Email notifications**:  
  - Configured for Zoho Mail (supports `smtp.zoho.com` and `smtp.zoho.eu`).  
  - On success: subject `[OK] …`, body with status, screenshot attached.  
  - On failure: subject `[ERROR] …`, body with the full Python traceback.

## Prerequisites

- A **GitHub repository** (public or private).  
- A **Zoho Mail account** (or adapt the email function to another SMTP provider).  
- An **app password** for Zoho (Settings → Security → App Passwords).  
- Basic familiarity with GitHub Actions and secrets.

## Setup

### 1. Clone or create the repository

    ```bash```
    git clone https://github.com/your-username/ripo-check-add-to-cart.git
    cd ripo-check-add-to-cart

## 2. Add the script and workflow

Place the following files in the repository:

- `monitor.py` – the full test script (copy the final version from this repository).
- `.github/workflows/hourly.yml` – the workflow definition.

## 3. Configure secrets

Go to your repository on GitHub → **Settings** → **Secrets and variables** → **Actions**. Add these three secrets:

| Secret name         | Value                                                      |
|---------------------|------------------------------------------------------------|
| `ZOHO_EMAIL`        | Your full Zoho email address (e.g., `name@zohomail.com`)   |
| `ZOHO_PASSWORD`     | The **app password** generated in Zoho (12‑character string, with or without hyphens) |
| `RECIPIENT_EMAIL`   | Email address that should receive the notifications        |

## 4. (Optional) Customise the SMTP server

If your Zoho account is hosted in a region other than US/EU, you can change the `SMTP_SERVERS` list in `monitor.py`. For example:

- `smtp.zoho.in` (India)
- `smtp.zoho.com.cn` (China)

The script automatically tries both `smtp.zoho.com` and `smtp.zoho.eu`; add your region’s server if needed.

## 5. Push the files

'bash'
git add monitor.py .github/workflows/hourly.yml
git commit -m "Add cart monitoring with email notifications"
git push origin main

## How It Works

### GitHub Actions Workflow

The workflow runs on `ubuntu-latest` and performs these steps:

1. Checkout the repository.
2. Setup Python 3.10.
3. Install Chrome (the latest stable version).
4. Install ChromeDriver (using the `nanasess/setup-chromedriver` action).
5. Install Python dependencies (only `selenium`).
6. Test email credentials – tries to log in to Zoho SMTP to catch auth issues early.
7. Run the monitor – executes `python monitor.py`.

All secrets are passed as environment variables.

### Script Behaviour

- **Headless Chrome** is used (no visible browser window).
- **Anti‑detection** flags are set to avoid bot blocking.
- **Pop‑ups** (geo‑ip, cookie consent) are closed if present; the script continues even if they are not found.
- **Menu navigation** is done by finding the first `<li><a>` in the main navigation, skipping a “Home” link if it exists. The doors link is either the second menu item or an `<a>` containing “durv”.
- **Product selection** uses CSS classes `.product-grid-item` or `.product`.
- **Accordions** (attribute selectors) are expanded; for some products (like doors) the first option is automatically selected to enable the Add‑to‑Cart button.
- **Overlays** after “Add to Cart” are closed if they appear.
- **Cart screenshot** is saved to a temporary file and attached to the success email.
- **Email** is sent using Zoho SMTP with TLS on port 587.

## Customisation

### Change the test frequency

Edit the `cron` expression in `.github/workflows/hourly.yml`:

    yaml
    schedule:
      - cron: '0 */2 * * *'   # every 2 hours

## Use a different email provider

Replace the `send_email_notification` function in `monitor.py` with your own SMTP settings (e.g., Gmail, Outlook, SendGrid). Example for Gmail:

    python
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

You will then need to use a Gmail App Password.

## Disable screenshots

Remove the screenshot block in the script or set a flag to skip it. The attachment step in `send_email_notification` will simply ignore a missing file.

## Run the test only once (locally)

You can execute the script directly on your machine (with `--headless` removed for debugging):

    bash
    python monitor.py

Make sure you have Chrome, ChromeDriver, and the required Python packages installed:

'bash'
pip install selenium

## Troubleshooting

### “StaleElementReferenceException”

This happens when a saved element reference is used after a page reload. The script is designed to **always find fresh elements** (see `_get_windows_menu_link()` and `_get_doors_menu_link()`). If you still see it, check that you are not storing elements across `driver.get()` calls.

### Email authentication fails

- Verify that you used an **app password**, not your account password.
- Check that your Zoho account region matches one of the SMTP servers.
- Ensure the secrets are correctly set and contain no extra spaces.
- Test connectivity with the “Test email credentials” step in the workflow.

### Category link not found

The script prints the first 50,000 characters of the page source in the workflow log. Look for the “ALL LINKS ON PAGE” block to see the actual menu link texts. Then adjust the selectors in `_get_windows_menu_link()` or `_get_doors_menu_link()` accordingly.

### Timeouts

If the site is slow, increase the `WebDriverWait` timeout (currently 90 seconds) in `test_ripo_add_to_cart` (e.g., `wait = WebDriverWait(driver, 120)`).

## Files in This Repository

| File | Description |
|------|-------------|
| `monitor.py` | The main Selenium test script. |
| `.github/workflows/hourly.yml` | GitHub Actions workflow definition. |
| `README.md` | This file. |

## License

This project is for personal/educational use. No warranty is provided.

## Contact

For issues, open a ticket in the GitHub repository or contact the maintainer directly.
