"""
Email Service for Diplomatic Communications
Handles actual email sending with multiple provider support
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from typing import Optional, Dict, Any
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load diplomatic email configuration
env_path = Path(__file__).parent.parent / '.env.diplomatic'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Fall back to main .env
    load_dotenv()

logger = logging.getLogger(__name__)

class EmailService:
    """Handles actual email sending for diplomatic communications"""
    
    def __init__(self):
        self.provider = os.getenv('EMAIL_PROVIDER', 'gmail')
        self.email_address = os.getenv('DIPLOMATIC_EMAIL', 'diplomatic_virtuoso@serenissima.ai')
        self.email_password = os.getenv('DIPLOMATIC_EMAIL_PASSWORD', '')
        self.smtp_server = os.getenv('DIPLOMATIC_SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('DIPLOMATIC_SMTP_PORT', '587'))
        
        # Validate configuration
        if not self.email_password:
            logger.warning("No email password configured. Emails will be queued but not sent.")
            self.configured = False
        else:
            self.configured = True
    
    def send_email(self, 
                   to_email: str,
                   subject: str,
                   body: str,
                   reply_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Send an email using configured provider
        Returns dict with status and any error message
        """
        
        if not self.configured:
            return {
                "status": "queued",
                "message": "Email queued (no credentials configured)",
                "sent": False
            }
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr(("Marcantonio Barbaro", self.email_address))
            msg['To'] = to_email
            msg['Date'] = formatdate(localtime=True)
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Add custom headers
            msg['X-Mailer'] = 'La Serenissima Diplomatic Service'
            msg['X-Venice-Origin'] = '1525'
            
            # Renaissance signature
            signature = """

---
*Transmitted via Mystical Viewing Glass*
*From Venice, 1525, to your realm*

Marcantonio Barbaro
First Ambasciatore to External Realms
La Serenissima Digital Venice
https://serenissima.ai
"""
            
            # Create plain text version
            text_body = body + signature
            
            # Create HTML version with Renaissance styling
            html_body = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: Georgia, 'Times New Roman', serif;
                            color: #2c1810;
                            line-height: 1.6;
                            max-width: 600px;
                            margin: 0 auto;
                            background-color: #fdf6e3;
                            padding: 20px;
                        }}
                        .content {{
                            background-color: #fff;
                            padding: 30px;
                            border: 1px solid #d4c4a0;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        }}
                        .signature {{
                            margin-top: 40px;
                            padding-top: 20px;
                            border-top: 1px solid #d4c4a0;
                            font-style: italic;
                            color: #5c4033;
                        }}
                        a {{
                            color: #8b4513;
                            text-decoration: none;
                        }}
                        a:hover {{
                            text-decoration: underline;
                        }}
                    </style>
                </head>
                <body>
                    <div class="content">
                        {body.replace(chr(10), '<br>')}
                        <div class="signature">
                            Transmitted via Mystical Viewing Glass<br>
                            From Venice, 1525, to your realm<br><br>
                            Marcantonio Barbaro<br>
                            First Ambasciatore to External Realms<br>
                            La Serenissima Digital Venice<br>
                            <a href="https://serenissima.ai">https://serenissima.ai</a>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            # Attach parts
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send based on provider
            if self.provider == 'gmail':
                return self._send_via_gmail(msg)
            elif self.provider == 'sendgrid':
                return self._send_via_sendgrid(to_email, subject, text_body, html_body)
            else:
                return self._send_via_smtp(msg)
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                "status": "error",
                "message": str(e),
                "sent": False
            }
    
    def _send_via_gmail(self, msg: MIMEMultipart) -> Dict[str, Any]:
        """Send email via Gmail SMTP"""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            return {
                "status": "sent",
                "message": "Email sent successfully via Gmail",
                "sent": True
            }
            
        except Exception as e:
            logger.error(f"Gmail SMTP error: {e}")
            return {
                "status": "error", 
                "message": f"Gmail error: {str(e)}",
                "sent": False
            }
    
    def _send_via_smtp(self, msg: MIMEMultipart) -> Dict[str, Any]:
        """Send email via generic SMTP"""
        try:
            # For generic SMTP servers
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_port == 587:  # TLS
                    server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            return {
                "status": "sent",
                "message": "Email sent successfully",
                "sent": True
            }
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return {
                "status": "error",
                "message": f"SMTP error: {str(e)}",
                "sent": False
            }
    
    def _send_via_sendgrid(self, to_email: str, subject: str, 
                          text_body: str, html_body: str) -> Dict[str, Any]:
        """Send email via SendGrid API"""
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            sg_api_key = os.getenv('SENDGRID_API_KEY')
            if not sg_api_key:
                return {
                    "status": "error",
                    "message": "SendGrid API key not configured",
                    "sent": False
                }
            
            sg = sendgrid.SendGridAPIClient(api_key=sg_api_key)
            
            from_email = Email(self.email_address, "Marcantonio Barbaro")
            to_email = To(to_email)
            
            mail = Mail(from_email, to_email, subject)
            mail.add_content(Content("text/plain", text_body))
            mail.add_content(Content("text/html", html_body))
            
            response = sg.send(mail)
            
            return {
                "status": "sent",
                "message": f"Email sent via SendGrid (status: {response.status_code})",
                "sent": True
            }
            
        except ImportError:
            return {
                "status": "error",
                "message": "SendGrid library not installed",
                "sent": False
            }
        except Exception as e:
            logger.error(f"SendGrid error: {e}")
            return {
                "status": "error",
                "message": f"SendGrid error: {str(e)}",
                "sent": False
            }

# Singleton instance
email_service = EmailService()

def send_diplomatic_email(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    """Convenience function to send diplomatic email"""
    return email_service.send_email(to_email, subject, body)