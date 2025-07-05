#!/usr/bin/env python3
"""
Mock API server for testing grievance endpoints locally
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
from datetime import datetime
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pyairtable import Api
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Airtable
api_key = os.environ.get('AIRTABLE_API_KEY')
base_id = os.environ.get('AIRTABLE_BASE_ID')

if api_key and base_id:
    api = Api(api_key)
    grievances_table = api.table(base_id, 'GRIEVANCES')
    support_table = api.table(base_id, 'GRIEVANCE_SUPPORT')
else:
    grievances_table = None
    support_table = None

@app.get("/")
async def root():
    return {"message": "Mock Grievance API is running"}

@app.get("/api/governance/grievances")
async def get_grievances(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    citizen: Optional[str] = Query(None),
    min_support: Optional[int] = Query(None),
):
    """Get list of grievances with optional filters."""
    if not grievances_table:
        return {
            "grievances": [],
            "total": 0,
            "message": "Airtable not configured"
        }
    
    try:
        records = grievances_table.all()
        grievances = []
        
        for record in records:
            fields = record['fields']
            
            # Apply filters
            if category and fields.get('Category') != category:
                continue
            if status and fields.get('Status') != status:
                continue
            if citizen and fields.get('Citizen') != citizen:
                continue
            if min_support and fields.get('SupportCount', 0) < min_support:
                continue
            
            grievance_data = {
                'id': record['id'],
                'citizen': fields.get('Citizen', 'Unknown'),
                'category': fields.get('Category', 'general'),
                'title': fields.get('Title', 'Untitled'),
                'description': fields.get('Description', ''),
                'status': fields.get('Status', 'filed'),
                'support_count': fields.get('SupportCount', 0),
                'filed_at': fields.get('FiledAt', ''),
                'reviewed_at': fields.get('ReviewedAt', None),
                'resolution': fields.get('Resolution', None)
            }
            grievances.append(grievance_data)
        
        # Sort by support count or date
        grievances.sort(key=lambda g: g['support_count'], reverse=True)
        
        return {
            "grievances": grievances,
            "total": len(grievances)
        }
        
    except Exception as e:
        return {
            "grievances": [],
            "total": 0,
            "error": str(e)
        }

@app.get("/api/governance/stats")
async def get_governance_stats():
    """Get governance participation statistics."""
    try:
        if not grievances_table:
            return {
                "total_grievances": 0,
                "total_supporters": 0,
                "average_support": 0,
                "top_categories": {}
            }
        
        grievances = grievances_table.all()
        
        # Calculate stats
        total_support = sum(g['fields'].get('SupportCount', 0) for g in grievances)
        categories = {}
        for g in grievances:
            cat = g['fields'].get('Category', 'general')
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_grievances": len(grievances),
            "total_supporters": total_support,
            "average_support": total_support / len(grievances) if grievances else 0,
            "top_categories": categories
        }
        
    except Exception as e:
        return {
            "total_grievances": 0,
            "total_supporters": 0,
            "average_support": 0,
            "top_categories": {},
            "error": str(e)
        }

@app.get("/api/governance/proposals")
async def get_proposals():
    """Placeholder for future proposal system."""
    return {
        "proposals": [],
        "message": "Proposal system coming in Phase 2 of democracy"
    }

if __name__ == "__main__":
    print("Starting mock grievance API server...")
    print("Access at: http://localhost:8002")
    print("\nAvailable endpoints:")
    print("  GET /api/governance/grievances")
    print("  GET /api/governance/stats")
    print("  GET /api/governance/proposals")
    uvicorn.run(app, host="0.0.0.0", port=8002)