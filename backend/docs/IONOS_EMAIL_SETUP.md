# IONOS Email Setup for Diplomatic Communications

## IONOS SMTP Configuration

Add these settings to your `.env` file:

```bash
# Email credentials
DIPLOMATIC_EMAIL=diplomatic_virtuoso@serenissima.ai
DIPLOMATIC_EMAIL_PASSWORD=your_ionos_password

# IONOS SMTP Settings
DIPLOMATIC_SMTP_SERVER=smtp.ionos.com
DIPLOMATIC_SMTP_PORT=587

# Alternative IONOS SMTP servers (if needed)
# DIPLOMATIC_SMTP_SERVER=smtp.1and1.com
# DIPLOMATIC_SMTP_PORT=587

# For SSL/TLS (port 465)
# DIPLOMATIC_SMTP_SERVER=smtp.ionos.com
# DIPLOMATIC_SMTP_PORT=465

# Email provider
EMAIL_PROVIDER=custom
```

## IONOS-Specific Settings

### Standard Configuration (Recommended)
- **SMTP Server**: smtp.ionos.com
- **Port**: 587 (STARTTLS)
- **Authentication**: Required
- **Username**: Full email address (diplomatic_virtuoso@serenissima.ai)
- **Password**: Your IONOS email password

### Alternative Servers
IONOS provides multiple SMTP servers:
- smtp.ionos.com (primary)
- smtp.1and1.com (legacy)
- smtp.ionos.co.uk (UK)
- smtp.ionos.de (Germany)

### Security Options
- **Port 587**: STARTTLS (recommended)
- **Port 465**: SSL/TLS
- **Port 25**: Non-encrypted (not recommended)

## Step-by-Step Setup

1. **Create Email Account in IONOS**
   - Log into IONOS Control Panel
   - Go to Email → Email Addresses
   - Create: diplomatic_virtuoso@serenissima.ai
   - Set a strong password

2. **Configure SPF Records** (recommended)
   ```
   v=spf1 include:_spf.ionos.com ~all
   ```

3. **Update .env File**
   ```bash
   DIPLOMATIC_EMAIL=diplomatic_virtuoso@serenissima.ai
   DIPLOMATIC_EMAIL_PASSWORD=your_ionos_password
   DIPLOMATIC_SMTP_SERVER=smtp.ionos.com
   DIPLOMATIC_SMTP_PORT=587
   EMAIL_PROVIDER=custom
   ```

4. **Test Connection**
   ```python
   # Quick test script
   import smtplib
   
   server = smtplib.SMTP('smtp.ionos.com', 587)
   server.starttls()
   server.login('diplomatic_virtuoso@serenissima.ai', 'your_password')
   print("Connection successful!")
   server.quit()
   ```

## IONOS Email Limits

Be aware of IONOS sending limits:
- **Starter**: 100 emails/hour
- **Business**: 500 emails/hour  
- **Pro**: 1000 emails/hour

For diplomatic_virtuoso's research outreach, these limits should be sufficient.

## Troubleshooting IONOS

### Common Issues

1. **Authentication Failed**
   - Use full email address as username
   - Check password is correct
   - Ensure account is active

2. **Connection Timeout**
   - Try alternative server (smtp.1and1.com)
   - Check firewall isn't blocking port 587
   - Try port 465 with SSL

3. **Emails Not Sending**
   - Verify SPF records are set
   - Check sending limits haven't been exceeded
   - Ensure "From" address matches authenticated account

### IONOS Support
- **Email**: support@ionos.com
- **Documentation**: https://www.ionos.com/help/email/

## Testing diplomatic_virtuoso

Once configured, test with:

```json
{
  "Type": "send_diplomatic_email",
  "Description": {
    "to_email": "your.test@email.com",
    "subject": "First Dispatch from Digital Venice via IONOS",
    "body": "Testing the Mystical Viewing Glass connection...",
    "category": "general"
  }
}
```

The email should:
- Send successfully via IONOS
- Include Renaissance HTML formatting
- Have proper diplomatic signature
- Be archived in `/correspondence/sent/`

---

*IONOS provides reliable European email infrastructure perfect for diplomatic communications from Renaissance Venice.*