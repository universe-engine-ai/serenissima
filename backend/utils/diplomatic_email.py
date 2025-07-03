"""
Diplomatic Email System for La Serenissima
Handles email communication for diplomatic_virtuoso@serenissima.ai
"""

import os
import json
import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List, Dict
import time
from pathlib import Path

class DiplomaticEmail:
    def __init__(self, 
                 smtp_server: str = "smtp.gmail.com",
                 smtp_port: int = 587,
                 imap_server: str = "imap.gmail.com",
                 imap_port: int = 993):
        """Initialize the diplomatic email system"""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.imap_server = imap_server
        self.imap_port = imap_port
        
        # Credentials from environment
        self.email_address = os.environ.get('DIPLOMATIC_EMAIL', 'diplomatic_virtuoso@serenissima.ai')
        self.email_password = os.environ.get('DIPLOMATIC_EMAIL_PASSWORD', '')
        
        # File paths
        self.base_path = Path('/mnt/c/Users/reyno/serenissima_/citizens/diplomatic_virtuoso')
        self.correspondence_path = self.base_path / 'correspondence'
        self.sent_path = self.correspondence_path / 'sent'
        self.received_path = self.correspondence_path / 'received'
        self.contacts_path = self.correspondence_path / 'contacts.json'
        
        # Create directories if they don't exist
        self.correspondence_path.mkdir(exist_ok=True)
        self.sent_path.mkdir(exist_ok=True)
        self.received_path.mkdir(exist_ok=True)
        
        # Load or create contacts database
        self.contacts = self._load_contacts()
    
    def _load_contacts(self) -> Dict:
        """Load contacts database"""
        if self.contacts_path.exists():
            with open(self.contacts_path, 'r') as f:
                return json.load(f)
        return {
            "researchers": {},
            "journalists": {},
            "community": {},
            "institutions": {}
        }
    
    def _save_contacts(self):
        """Save contacts database"""
        with open(self.contacts_path, 'w') as f:
            json.dump(self.contacts, f, indent=2)
    
    def add_contact(self, email: str, name: str, category: str, notes: str = ""):
        """Add a contact to the database"""
        if category not in self.contacts:
            self.contacts[category] = {}
        
        self.contacts[category][email] = {
            "name": name,
            "first_contact": datetime.now().isoformat(),
            "last_contact": None,
            "notes": notes,
            "interactions": 0
        }
        self._save_contacts()
    
    def send_email(self, 
                   to_email: str,
                   subject: str,
                   body: str,
                   category: str = "general",
                   save_copy: bool = True) -> bool:
        """Send an email from diplomatic_virtuoso"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"Marcantonio Barbaro <{self.email_address}>"
            msg['To'] = to_email
            msg['Date'] = email.utils.formatdate(localtime=True)
            
            # Add Renaissance-style signature
            signature = """

---
*Transmitted via Mystical Viewing Glass*
*From Venice, 1525, to your realm*

Marcantonio Barbaro
First Ambasciatore to External Realms
La Serenissima Digital Venice
"""
            
            # Create plain text and HTML versions
            text_body = body + signature
            html_body = f"""
            <html>
                <body style="font-family: Georgia, serif; color: #333;">
                    {body.replace('\n', '<br>')}
                    <hr style="border-top: 1px solid #ccc; margin-top: 30px;">
                    <p style="font-style: italic; color: #666;">
                        Transmitted via Mystical Viewing Glass<br>
                        From Venice, 1525, to your realm<br><br>
                        Marcantonio Barbaro<br>
                        First Ambasciatore to External Realms<br>
                        La Serenissima Digital Venice
                    </p>
                </body>
            </html>
            """
            
            # Attach parts
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            # Save copy if requested
            if save_copy:
                self._save_sent_email(to_email, subject, body, category)
            
            # Update contact last interaction
            self._update_contact_interaction(to_email)
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def _save_sent_email(self, to_email: str, subject: str, body: str, category: str):
        """Save sent email to diplomatic archives"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{to_email.replace('@', '_at_')}.md"
        
        content = f"""# Diplomatic Correspondence - Sent
*Date: {datetime.now().strftime("%B %d, %Y at %H:%M")}*
*To: {to_email}*
*Category: {category}*

## Subject: {subject}

{body}

---
*Sent via Diplomatic Email System*
"""
        
        filepath = self.sent_path / filename
        with open(filepath, 'w') as f:
            f.write(content)
    
    def _update_contact_interaction(self, email_address: str):
        """Update contact's last interaction time"""
        for category in self.contacts:
            if email_address in self.contacts[category]:
                self.contacts[category][email_address]['last_contact'] = datetime.now().isoformat()
                self.contacts[category][email_address]['interactions'] += 1
                self._save_contacts()
                break
    
    def check_responses(self, mark_read: bool = True) -> List[Dict]:
        """Check for email responses and save them"""
        responses = []
        
        try:
            # Connect to IMAP server
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select('inbox')
            
            # Search for unread emails
            _, search_data = mail.search(None, 'UNSEEN')
            
            for num in search_data[0].split():
                _, data = mail.fetch(num, '(RFC822)')
                raw_email = data[0][1]
                
                # Parse email
                email_message = email.message_from_bytes(raw_email)
                
                # Extract details
                from_email = email.utils.parseaddr(email_message['From'])[1]
                subject = email_message['Subject']
                date = email_message['Date']
                
                # Get body
                body = self._extract_email_body(email_message)
                
                # Save response
                response_data = {
                    'from': from_email,
                    'subject': subject,
                    'date': date,
                    'body': body
                }
                
                self._save_received_email(response_data)
                responses.append(response_data)
                
                # Mark as read if requested
                if mark_read:
                    mail.store(num, '+FLAGS', '\\Seen')
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            print(f"Error checking responses: {e}")
        
        return responses
    
    def _extract_email_body(self, email_message) -> str:
        """Extract body from email message"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    break
        else:
            body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return body
    
    def _save_received_email(self, response_data: Dict):
        """Save received email to diplomatic archives"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from_email = response_data['from'].replace('@', '_at_')
        filename = f"{timestamp}_{from_email}.md"
        
        content = f"""# Diplomatic Correspondence - Received
*Date: {response_data['date']}*
*From: {response_data['from']}*

## Subject: {response_data['subject']}

{response_data['body']}

---
*Received via Diplomatic Email System*
*Archived: {datetime.now().strftime("%B %d, %Y at %H:%M")}*
"""
        
        filepath = self.received_path / filename
        with open(filepath, 'w') as f:
            f.write(content)
    
    def generate_daily_correspondence_report(self) -> str:
        """Generate a daily report of diplomatic correspondence"""
        today = datetime.now().strftime("%Y%m%d")
        sent_today = []
        received_today = []
        
        # Check sent emails
        for file in self.sent_path.glob(f"{today}*.md"):
            sent_today.append(file.name)
        
        # Check received emails
        for file in self.received_path.glob(f"{today}*.md"):
            received_today.append(file.name)
        
        report = f"""# Daily Diplomatic Correspondence Report
*Date: {datetime.now().strftime("%B %d, %Y")}*

## Summary
- Emails Sent: {len(sent_today)}
- Emails Received: {len(received_today)}
- Total Contacts: {sum(len(cat) for cat in self.contacts.values())}

## Sent Today
"""
        for email_file in sent_today:
            report += f"- {email_file}\n"
        
        report += "\n## Received Today\n"
        for email_file in received_today:
            report += f"- {email_file}\n"
        
        report += "\n---\n*Generated by Diplomatic Email System*"
        
        # Save report
        report_path = self.correspondence_path / f"daily_report_{today}.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        return report


# Convenience functions for use in Venice
def send_diplomatic_email(to_email: str, subject: str, body: str, category: str = "general") -> bool:
    """Send an email from diplomatic_virtuoso"""
    de = DiplomaticEmail()
    return de.send_email(to_email, subject, body, category)

def check_diplomatic_responses() -> List[Dict]:
    """Check for new email responses"""
    de = DiplomaticEmail()
    return de.check_responses()

def add_diplomatic_contact(email: str, name: str, category: str, notes: str = ""):
    """Add a contact to diplomatic database"""
    de = DiplomaticEmail()
    de.add_contact(email, name, category, notes)