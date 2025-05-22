"""
Google Docs utilities for the backlink agent
"""
import os
from typing import Dict
from datetime import datetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

load_dotenv()

class GoogleDocsManager:
    def __init__(self):
        self.service = self._setup_service()
        self.doc_id = os.getenv("GOOGLE_DOC_ID")
    
    def _setup_service(self):
        """Setup Google Docs API service"""
        try:
            creds = Credentials.from_service_account_file(
                os.getenv("GOOGLE_CREDENTIALS_FILE"),
                scopes=['https://www.googleapis.com/auth/documents']
            )
            return build('docs', 'v1', credentials=creds)
        except Exception as e:
            print(f"Google Docs setup failed: {e}")
            return None
    
    def insert_opportunity(self, opportunity: Dict) -> Dict:
        """Insert a new opportunity into the document"""
        if not self.service:
            return {"status": "error", "message": "Google Docs not configured"}
            
        try:
            content = self._format_opportunity(opportunity)
            requests = [{
                'insertText': {
                    'location': {'index': 1},
                    'text': content
                }
            }]
            
            self.service.documents().batchUpdate(
                documentId=self.doc_id,
                body={'requests': requests}
            ).execute()
            
            return {"status": "success", "message": "Document updated"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _format_opportunity(self, opportunity: Dict) -> str:
        """Format opportunity data for insertion"""
        timestamp = opportunity.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""
=== GUEST POST OPPORTUNITY ===
Date: {timestamp}
Site: {opportunity.get('site_name', 'N/A')}
URL: {opportunity.get('url', 'N/A')}
Email: {opportunity.get('email', 'N/A')}
Contact Method: {opportunity.get('contact_method', 'N/A')}
Status: {opportunity.get('status', 'N/A')}
Email Status: {opportunity.get('email_status', 'N/A')}
Email Sent At: {opportunity.get('email_sent_at', 'N/A')}
Guidelines: {opportunity.get('guidelines', 'N/A')}
Notes: {opportunity.get('notes', 'N/A')}
---

""" 