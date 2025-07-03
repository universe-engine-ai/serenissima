"""
Diplomatic Communications API for La Serenissima
Handles external communications for the Ambasciatore
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
import json
from pathlib import Path
import hashlib
import asyncio

router = APIRouter(prefix="/api/diplomatic", tags=["diplomatic"])

# File paths
BASE_PATH = Path('/mnt/c/Users/reyno/serenissima_/citizens/diplomatic_virtuoso')
CORRESPONDENCE_PATH = BASE_PATH / 'correspondence'
OUTBOX_PATH = CORRESPONDENCE_PATH / 'outbox'
SENT_PATH = CORRESPONDENCE_PATH / 'sent'
RECEIVED_PATH = CORRESPONDENCE_PATH / 'received'
CONTACTS_PATH = CORRESPONDENCE_PATH / 'contacts.json'

# Ensure directories exist
for path in [CORRESPONDENCE_PATH, OUTBOX_PATH, SENT_PATH, RECEIVED_PATH]:
    path.mkdir(parents=True, exist_ok=True)

# Models
class DiplomaticEmail(BaseModel):
    to_email: EmailStr
    subject: str
    body: str
    category: Optional[str] = "general"
    research_area: Optional[str] = None
    
class EmailResponse(BaseModel):
    from_email: EmailStr
    subject: str
    body: str
    received_at: datetime
    
class Contact(BaseModel):
    email: EmailStr
    name: str
    category: str
    institution: Optional[str] = None
    research_area: Optional[str] = None
    notes: Optional[str] = ""

# Helper functions
def load_contacts() -> Dict:
    """Load contacts database"""
    if CONTACTS_PATH.exists():
        with open(CONTACTS_PATH, 'r') as f:
            return json.load(f)
    return {
        "researchers": {},
        "journalists": {},
        "community": {},
        "institutions": {},
        "general": {}
    }

def save_contacts(contacts: Dict):
    """Save contacts database"""
    with open(CONTACTS_PATH, 'w') as f:
        json.dump(contacts, f, indent=2)

def generate_email_id(email_data: DiplomaticEmail) -> str:
    """Generate unique ID for email"""
    content = f"{email_data.to_email}{email_data.subject}{datetime.now().isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()[:8]

# API Endpoints
@router.post("/send-email")
async def send_diplomatic_email(email_data: DiplomaticEmail, background_tasks: BackgroundTasks):
    """
    Queue an email for sending from diplomatic_virtuoso@serenissima.ai
    The actual sending happens asynchronously
    """
    try:
        # Generate email ID
        email_id = generate_email_id(email_data)
        timestamp = datetime.now()
        
        # Create email record
        email_record = {
            "id": email_id,
            "to": email_data.to_email,
            "subject": email_data.subject,
            "body": email_data.body,
            "category": email_data.category,
            "research_area": email_data.research_area,
            "queued_at": timestamp.isoformat(),
            "status": "queued"
        }
        
        # Save to outbox
        outbox_file = OUTBOX_PATH / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{email_id}.json"
        with open(outbox_file, 'w') as f:
            json.dump(email_record, f, indent=2)
        
        # Also create markdown version for diplomatic_virtuoso to review
        md_content = f"""# Diplomatic Dispatch - Queued
*ID: {email_id}*
*Date: {timestamp.strftime("%B %d, %Y at %H:%M")}*
*To: {email_data.to_email}*
*Category: {email_data.category}*
{f'*Research Area: {email_data.research_area}*' if email_data.research_area else ''}

## Subject: {email_data.subject}

{email_data.body}

---
*Status: Queued for transmission via Mystical Viewing Glass*
"""
        
        md_file = OUTBOX_PATH / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{email_id}.md"
        with open(md_file, 'w') as f:
            f.write(md_content)
        
        # Add background task to process sending
        background_tasks.add_task(process_email_queue)
        
        return {
            "status": "queued",
            "email_id": email_id,
            "message": "Email queued for diplomatic transmission"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/receive-response")
async def receive_email_response(response: EmailResponse):
    """
    Record an email response received by diplomatic_virtuoso
    """
    try:
        timestamp = datetime.now()
        response_id = hashlib.md5(
            f"{response.from_email}{response.subject}{timestamp.isoformat()}".encode()
        ).hexdigest()[:8]
        
        # Save response
        response_data = {
            "id": response_id,
            "from": response.from_email,
            "subject": response.subject,
            "body": response.body,
            "received_at": response.received_at.isoformat(),
            "archived_at": timestamp.isoformat()
        }
        
        # Save JSON version
        json_file = RECEIVED_PATH / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{response_id}.json"
        with open(json_file, 'w') as f:
            json.dump(response_data, f, indent=2)
        
        # Save markdown version for easy reading
        md_content = f"""# Diplomatic Correspondence - Received
*ID: {response_id}*
*Received: {response.received_at.strftime("%B %d, %Y at %H:%M")}*
*From: {response.from_email}*

## Subject: {response.subject}

{response.body}

---
*Archived: {timestamp.strftime("%B %d, %Y at %H:%M")}*
*Via Mystical Viewing Glass*
"""
        
        md_file = RECEIVED_PATH / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{response_id}.md"
        with open(md_file, 'w') as f:
            f.write(md_content)
        
        # Update contact if exists
        contacts = load_contacts()
        for category in contacts:
            if response.from_email in contacts[category]:
                contacts[category][response.from_email]['last_contact'] = timestamp.isoformat()
                contacts[category][response.from_email]['interactions'] = \
                    contacts[category][response.from_email].get('interactions', 0) + 1
                save_contacts(contacts)
                break
        
        return {
            "status": "received",
            "response_id": response_id,
            "message": "Response archived in diplomatic correspondence"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-contact")
async def add_diplomatic_contact(contact: Contact):
    """Add a contact to the diplomatic database"""
    try:
        contacts = load_contacts()
        
        if contact.category not in contacts:
            contacts[contact.category] = {}
        
        contacts[contact.category][contact.email] = {
            "name": contact.name,
            "institution": contact.institution,
            "research_area": contact.research_area,
            "first_contact": datetime.now().isoformat(),
            "last_contact": None,
            "notes": contact.notes,
            "interactions": 0
        }
        
        save_contacts(contacts)
        
        return {
            "status": "added",
            "message": f"Contact {contact.name} added to {contact.category} category"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/correspondence-summary")
async def get_correspondence_summary():
    """Get summary of diplomatic correspondence"""
    try:
        # Count emails
        outbox_count = len(list(OUTBOX_PATH.glob("*.json")))
        sent_count = len(list(SENT_PATH.glob("*.json")))
        received_count = len(list(RECEIVED_PATH.glob("*.json")))
        
        # Count contacts
        contacts = load_contacts()
        contact_counts = {cat: len(contacts[cat]) for cat in contacts}
        total_contacts = sum(contact_counts.values())
        
        # Recent activity
        today = datetime.now().strftime("%Y%m%d")
        sent_today = len(list(SENT_PATH.glob(f"{today}*.json")))
        received_today = len(list(RECEIVED_PATH.glob(f"{today}*.json")))
        
        return {
            "emails": {
                "queued": outbox_count,
                "sent": sent_count,
                "received": received_count,
                "sent_today": sent_today,
                "received_today": received_today
            },
            "contacts": {
                "total": total_contacts,
                "by_category": contact_counts
            },
            "status": "Diplomatic channels operational"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/research-interests")
async def get_research_interests():
    """Get summary of research interests from correspondence"""
    try:
        research_areas = {}
        
        # Analyze sent emails
        for json_file in SENT_PATH.glob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
                if 'research_area' in data and data['research_area']:
                    area = data['research_area']
                    research_areas[area] = research_areas.get(area, 0) + 1
        
        # Sort by frequency
        sorted_areas = sorted(research_areas.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "research_interests": sorted_areas,
            "total_research_contacts": sum(research_areas.values())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background task
async def process_email_queue():
    """Process queued emails (placeholder for actual sending)"""
    # In production, this would integrate with actual email service
    # For now, it just moves emails from outbox to sent after a delay
    await asyncio.sleep(5)  # Simulate sending delay
    
    # Move processed emails from outbox to sent
    for json_file in OUTBOX_PATH.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                email_data = json.load(f)
            
            # Update status
            email_data['status'] = 'sent'
            email_data['sent_at'] = datetime.now().isoformat()
            
            # Save to sent folder
            new_file = SENT_PATH / json_file.name
            with open(new_file, 'w') as f:
                json.dump(email_data, f, indent=2)
            
            # Remove from outbox
            json_file.unlink()
            
            # Also move the markdown file
            md_file = json_file.with_suffix('.md')
            if md_file.exists():
                new_md = SENT_PATH / md_file.name
                md_file.rename(new_md)
                
        except Exception as e:
            print(f"Error processing email: {e}")