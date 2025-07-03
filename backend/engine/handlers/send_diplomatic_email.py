"""
Send Diplomatic Email Handler
Allows diplomatic_virtuoso to send emails to external realm
"""

import json
from datetime import datetime
from pathlib import Path
import hashlib

def handle_send_diplomatic_email(citizenUsername: str, activity: dict, test_mode: bool = False) -> str:
    """
    Handle sending diplomatic email to external realm
    Only diplomatic_virtuoso can use this activity
    """
    
    # Verify this is diplomatic_virtuoso
    if citizenUsername != "diplomatic_virtuoso":
        error_msg = f"Unauthorized: Only diplomatic_virtuoso can send external emails"
        return error_msg
    
    # Extract email details from activity description
    try:
        # Parse email data from activity description (JSON format expected)
        email_data = json.loads(activity.get("Description", "{}"))
        
        to_email = email_data.get("to_email")
        subject = email_data.get("subject")
        body = email_data.get("body")
        category = email_data.get("category", "general")
        research_area = email_data.get("research_area", None)
        
        if not all([to_email, subject, body]):
            raise ValueError("Missing required email fields: to_email, subject, body")
        
        # Generate email ID
        email_id = hashlib.md5(
            f"{to_email}{subject}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:8]
        
        # Paths
        base_path = Path('/mnt/c/Users/reyno/serenissima_/citizens/diplomatic_virtuoso')
        correspondence_path = base_path / 'correspondence'
        outbox_path = correspondence_path / 'outbox'
        
        # Ensure directories exist
        outbox_path.mkdir(parents=True, exist_ok=True)
        
        # Create email record
        timestamp = datetime.now()
        email_record = {
            "id": email_id,
            "to": to_email,
            "subject": subject,
            "body": body,
            "category": category,
            "research_area": research_area,
            "queued_at": timestamp.isoformat(),
            "activity_id": activity["id"],
            "status": "queued"
        }
        
        # Save to outbox (JSON)
        json_file = outbox_path / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{email_id}.json"
        with open(json_file, 'w') as f:
            json.dump(email_record, f, indent=2)
        
        # Create markdown version for review
        md_content = f"""# Diplomatic Dispatch - Via Activity System
*ID: {email_id}*
*Date: {timestamp.strftime("%B %d, %Y at %H:%M")}*
*To: {to_email}*
*Category: {category}*
{f'*Research Area: {research_area}*' if research_area else ''}

## Subject: {subject}

{body}

---
*Status: Queued for transmission via Mystical Viewing Glass*
*Activity ID: {activity["id"]}*

Marcantonio Barbaro
First Ambasciatore to External Realms
La Serenissima Digital Venice
"""
        
        md_file = outbox_path / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{email_id}.md"
        with open(md_file, 'w') as f:
            f.write(md_content)
        
        # Create a log entry
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "email_id": email_id,
            "to": to_email,
            "subject": subject,
            "category": category,
            "research_area": research_area
        }
        
        log_file = correspondence_path / "diplomatic_email_log.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Try to send the email immediately
        try:
            from backend.utils.email_service import send_diplomatic_email
            
            result = send_diplomatic_email(to_email, subject, body)
            
            if result['sent']:
                # Move to sent folder
                sent_path = correspondence_path / 'sent'
                sent_path.mkdir(exist_ok=True)
                
                # Update status
                email_record['status'] = 'sent'
                email_record['sent_at'] = datetime.now().isoformat()
                email_record['send_result'] = result
                
                # Move files to sent
                sent_json = sent_path / json_file.name
                with open(sent_json, 'w') as f:
                    json.dump(email_record, f, indent=2)
                json_file.unlink()
                
                sent_md = sent_path / md_file.name
                md_file.rename(sent_md)
                
                success_msg = f"Diplomatic email sent successfully! ID: {email_id}"
            else:
                # Email queued but not sent (no credentials or error)
                email_record['send_attempt'] = result
                with open(json_file, 'w') as f:
                    json.dump(email_record, f, indent=2)
                
                success_msg = f"Diplomatic email queued. ID: {email_id}. {result.get('message', '')}"
                
        except Exception as e:
            # Fallback to queued status
            success_msg = f"Diplomatic email queued (send service unavailable). ID: {email_id}"
        
        return success_msg
        
    except json.JSONDecodeError:
        error_msg = "Invalid email data format. Expected JSON in Description field"
        return error_msg
        
    except Exception as e:
        error_msg = f"Error sending diplomatic email: {str(e)}"
        return error_msg