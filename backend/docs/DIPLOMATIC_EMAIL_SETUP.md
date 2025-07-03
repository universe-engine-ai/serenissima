# Diplomatic Email Setup Guide

## Overview

The diplomatic email system allows diplomatic_virtuoso to send real emails from diplomatic_virtuoso@serenissima.ai to external researchers, journalists, and other contacts.

## Setup Steps

### 1. Create Email Account

First, create the email account diplomatic_virtuoso@serenissima.ai on your email provider:
- Google Workspace (recommended)
- SendGrid
- AWS SES
- Any SMTP-compatible email service

### 2. Configure Credentials

Add these environment variables to your `.env` file:

```bash
# Email credentials
DIPLOMATIC_EMAIL=diplomatic_virtuoso@serenissima.ai
DIPLOMATIC_EMAIL_PASSWORD=your_password_here

# SMTP Settings (Gmail example)
DIPLOMATIC_SMTP_SERVER=smtp.gmail.com
DIPLOMATIC_SMTP_PORT=587

# Email provider
EMAIL_PROVIDER=gmail
```

### 3. Gmail-Specific Setup

If using Gmail/Google Workspace:

1. Enable 2-Factor Authentication on the account
2. Generate an App Password:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
   - Use this as DIPLOMATIC_EMAIL_PASSWORD

3. Enable "Less secure app access" (if needed):
   - Google Account → Security → Less secure app access → Turn on

### 4. SendGrid Setup (Alternative)

For higher volume/reliability:

```bash
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=your_sendgrid_api_key_here
```

1. Create SendGrid account
2. Verify your domain (serenissima.ai)
3. Create API key with "Mail Send" permissions
4. Install sendgrid package: `pip install sendgrid`

### 5. Test the System

Test sending an email via the activity system:

```python
# Create test activity
{
    "Type": "send_diplomatic_email",
    "CitizenUsername": "diplomatic_virtuoso",
    "Description": json.dumps({
        "to_email": "test@example.com",
        "subject": "Test from Digital Venice",
        "body": "This is a test of the diplomatic email system.",
        "category": "general"
    })
}
```

### 6. Email Features

The system automatically:
- Adds Renaissance-themed HTML formatting
- Includes diplomatic signature
- Archives all correspondence
- Tracks contacts and interactions
- Queues emails if credentials missing

### 7. Monitoring

Check email status:
- Queued emails: `/correspondence/outbox/`
- Sent emails: `/correspondence/sent/`
- Email log: `/correspondence/diplomatic_email_log.jsonl`

### 8. Security Notes

- Store credentials securely (use .env, not in code)
- Limit sending to diplomatic_virtuoso only
- Consider rate limiting for production
- Monitor for bounce/spam issues
- Keep archives of all correspondence

## Troubleshooting

### Emails stuck in outbox
- Check credentials in .env
- Verify SMTP settings
- Check email service logs

### Authentication errors
- For Gmail: Use App Password, not account password
- Verify 2FA is enabled
- Check "Less secure apps" setting

### Emails marked as spam
- Set up SPF/DKIM records for serenissima.ai
- Use consistent from address
- Avoid spam trigger words
- Build sender reputation gradually

## Email Templates

The system includes:
- Renaissance-themed HTML design
- Automatic signature
- Custom headers (X-Venice-Origin: 1525)
- Reply tracking capabilities

## Next Steps

Once configured:
1. Test with friendly contacts first
2. Build sender reputation gradually
3. Monitor delivery rates
4. Collect responses in `/correspondence/received/`
5. Use data for diplomatic reports

---

*May your dispatches bridge realities with grace and authenticity.*