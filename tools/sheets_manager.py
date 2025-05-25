"""
Google Sheets manager for storing and updating guest posting opportunities
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv
import uuid

load_dotenv()

class GoogleSheetsManager:
    """Manages Google Sheets operations for guest posting opportunities"""
    
    def __init__(self):
        self.spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
        self.sheet_name = "back_link"
        self.service = self._setup_service()
        
    def _setup_service(self):
        """Set up Google Sheets API service"""
        try:
            # Get credentials from environment variable
            creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
            if not creds_path:
                raise ValueError("GOOGLE_SHEETS_CREDENTIALS environment variable is required")
            
            # Load credentials from file
            try:
                creds = Credentials.from_service_account_file(creds_path)
            except Exception as e:
                print(f"Error loading credentials from file {creds_path}: {e}")
                # Try parsing as JSON string
                try:
                    creds_dict = json.loads(creds_path)
                    creds = Credentials.from_service_account_info(creds_dict)
                except Exception as e2:
                    raise ValueError(f"Failed to load credentials from file or parse as JSON: {e2}")
            
            # Build service
            service = build('sheets', 'v4', credentials=creds)
            return service
            
        except Exception as e:
            print(f"Error setting up Google Sheets service: {e}")
            return None
    
    def add_opportunity(self, opportunity: Dict) -> bool:
        """Add a new opportunity to the sheet"""
        try:
            if not self.service:
                raise ValueError("Google Sheets service not initialized")
            
            print(f"\nAdding opportunity to sheet: {opportunity['site_name']}")
            print(f"Sheet ID: {self.spreadsheet_id}")
            print(f"Sheet name: {self.sheet_name}")
            
            # Generate a unique ID if not present
            if not opportunity.get('id'):
                opportunity['id'] = str(uuid.uuid4())
            
            # Prepare row data
            row = [
                opportunity.get('id', ''),
                opportunity.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                opportunity.get('site_name', ''),
                opportunity.get('url', ''),
                opportunity.get('email', ''),
                opportunity.get('contact_method', ''),
                opportunity.get('submission_form_url', ''),
                opportunity.get('status', 'pending'),
                opportunity.get('email_status', ''),
                opportunity.get('email_sent_at', ''),
                opportunity.get('guidelines', ''),
                opportunity.get('notes', ''),
                '',  # Follow-up Date
                ''   # Response Summary
            ]
            
            print(f"Prepared row data: {row}")
            
            # Append row to sheet
            body = {
                'values': [row]
            }
            
            print("Sending request to Google Sheets API...")
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A:N",
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            print(f"Google Sheets API response: {result}")
            return True
            
        except Exception as e:
            print(f"Error adding opportunity to sheets: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    
    def update_opportunity(self, opportunity: Dict) -> bool:
        """Update an existing opportunity in the sheet"""
        try:
            if not self.service:
                raise ValueError("Google Sheets service not initialized")
            
            # First, find the row with matching URL
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A:N"
            ).execute()
            
            values = result.get('values', [])
            row_index = None
            
            for i, row in enumerate(values):
                if len(row) >= 4 and row[3] == opportunity['url']:  # URL is in column D
                    row_index = i + 1  # Sheets is 1-indexed
                    break
            
            if row_index is None:
                print(f"Opportunity not found in sheet: {opportunity['url']}")
                return False
            
            # Prepare update data
            update_data = [
                opportunity.get('id', ''),
                opportunity.get('timestamp', ''),
                opportunity.get('site_name', ''),
                opportunity.get('url', ''),
                opportunity.get('email', ''),
                opportunity.get('contact_method', ''),
                opportunity.get('submission_form_url', ''),
                opportunity.get('status', ''),
                opportunity.get('email_status', ''),
                opportunity.get('email_sent_at', ''),
                opportunity.get('guidelines', ''),
                opportunity.get('notes', ''),
                '',  # Follow-up Date
                ''   # Response Summary
            ]
            
            # Update the row
            body = {
                'values': [update_data]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A{row_index}:N{row_index}",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating opportunity in sheets: {e}")
            return False
    
    def get_opportunities(self) -> List[Dict]:
        """Get all opportunities from the sheet"""
        try:
            if not self.service:
                raise ValueError("Google Sheets service not initialized")
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A:N"
            ).execute()
            
            values = result.get('values', [])
            opportunities = []
            
            # Skip header row
            for row in values[1:]:
                if len(row) >= 14:  # Ensure row has all columns
                    opportunity = {
                        'id': row[0],
                        'timestamp': row[1],
                        'site_name': row[2],
                        'url': row[3],
                        'email': row[4],
                        'contact_method': row[5],
                        'submission_form_url': row[6],
                        'status': row[7],
                        'email_status': row[8],
                        'email_sent_at': row[9],
                        'guidelines': row[10],
                        'notes': row[11],
                        'follow_up_date': row[12],
                        'response_summary': row[13]
                    }
                    opportunities.append(opportunity)
            
            return opportunities
            
        except Exception as e:
            print(f"Error getting opportunities from sheets: {e}")
            return [] 