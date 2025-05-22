"""
Google Sheets integration for the backlink agent
"""
import os
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

# Define the structure of the backlink spreadsheet
BACKLINK_COLUMNS = [
    "Date", 
    "Site Name", 
    "URL", 
    "Email", 
    "Contact Method", 
    "Form URL", 
    "Status", 
    "Email Status", 
    "Email Sent At", 
    "Guidelines", 
    "Notes", 
    "Follow-up Date", 
    "Response Summary"
]

class GoogleSheetsManager:
    def __init__(self):
        self.sheet_id = os.getenv("GOOGLE_SHEET_ID", "1hILPxBMD1nc0NPwzrE5Na9r4KAcDoYHV2bgPXsM8nKw")
        self.sheet_name = os.getenv("GOOGLE_SHEET_NAME", "back_links")
        self.creds = self._setup_credentials()
        self.client = self._setup_client()
        self.offline_mode = False
        self.spreadsheet, self.worksheet = self._setup_worksheet()
        
        if not self.spreadsheet or not self.worksheet:
            print("Failed to setup Google Sheets. Running in offline mode.")
            self.offline_mode = True
    
    def _setup_credentials(self):
        """Setup Google Sheets API credentials"""
        try:
            # These scopes are critical - must include both Drive and Sheets
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "google_sheets_credentials.json")
            
            if not os.path.exists(credentials_file):
                print(f"Warning: Credentials file {credentials_file} not found")
                return None
                
            return Credentials.from_service_account_file(
                credentials_file,
                scopes=scopes
            )
        except Exception as e:
            print(f"Google Sheets credentials setup failed: {e}")
            return None
    
    def _setup_client(self):
        """Setup gspread client"""
        if not self.creds:
            return None
        try:
            return gspread.authorize(self.creds)
        except Exception as e:
            print(f"Google Sheets client setup failed: {e}")
            return None
    
    def _setup_worksheet(self) -> Tuple[Optional[Any], Optional[Any]]:
        """Setup and return the spreadsheet and worksheet"""
        if not self.client:
            return None, None
            
        try:
            # Try opening by ID first (more reliable)
            try:
                spreadsheet = self.client.open_by_key(self.sheet_id)
                print(f"Successfully opened spreadsheet by ID: {self.sheet_id}")
            except gspread.exceptions.APIError as e:
                print(f"Error opening by ID: {e}")
                # Try to open by name as fallback
                spreadsheet = self.client.open(self.sheet_name)
                print(f"Opened spreadsheet by name: {self.sheet_name}")
            
            # Try to get the back_link worksheet or create it
            try:
                worksheet = spreadsheet.worksheet("back_link")  # Use hardcoded "back_link" as the worksheet name
                print(f"Found existing worksheet: back_link")
            except gspread.exceptions.WorksheetNotFound:
                print(f"Creating new worksheet: back_link")
                worksheet = spreadsheet.add_worksheet(title="back_link", rows=1000, cols=20)
            
            # Check if headers exist, add them if not
            try:
                headers = worksheet.row_values(1)
                if not headers or headers != BACKLINK_COLUMNS:
                    worksheet.clear()
                    worksheet.append_row(BACKLINK_COLUMNS)
                    print("Set up headers in the spreadsheet")
            except Exception as e:
                print(f"Error checking/setting headers: {e}")
                worksheet.append_row(BACKLINK_COLUMNS)
                
            return spreadsheet, worksheet
            
        except gspread.exceptions.SpreadsheetNotFound:
            # Create new spreadsheet if it doesn't exist
            try:
                print(f"Spreadsheet not found. Creating new one named: {self.sheet_name}")
                spreadsheet = self.client.create(self.sheet_name)
                # Share with owner by default
                owner_email = os.getenv("OWNER_EMAIL")
                if owner_email:
                    spreadsheet.share(owner_email, perm_type='user', role='owner')
                
                # Create the back_link worksheet
                worksheet = spreadsheet.add_worksheet(title="back_link", rows=1000, cols=20)
                worksheet.append_row(BACKLINK_COLUMNS)
                return spreadsheet, worksheet
            except Exception as e:
                print(f"Failed to create spreadsheet: {e}")
                return None, None
        except Exception as e:
            print(f"Error setting up worksheet: {e}")
            return None, None
    
    def insert_opportunity(self, opportunity: Dict) -> Dict:
        """Insert a new opportunity into the spreadsheet"""
        if self.offline_mode or not self.worksheet:
            print(f"[OFFLINE] Would add opportunity for {opportunity.get('site_name', 'unknown site')}")
            return {"status": "success", "message": "Offline mode - data not actually saved"}
            
        try:
            timestamp = opportunity.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Format data as a row
            row_data = [
                timestamp,
                opportunity.get('site_name', ''),
                opportunity.get('url', ''),
                opportunity.get('email', ''),
                opportunity.get('contact_method', ''),
                opportunity.get('submission_form_url', ''),
                opportunity.get('status', 'pending'),
                opportunity.get('email_status', ''),
                opportunity.get('email_sent_at', ''),
                opportunity.get('guidelines', '')[:1000] if opportunity.get('guidelines') else '',  # Truncate long text
                opportunity.get('notes', '')[:1000] if opportunity.get('notes') else '',  # Truncate long text
                '',  # Follow-up Date (empty initially)
                ''   # Response Summary (empty initially)
            ]
            
            # Append to sheet
            self.worksheet.append_row(row_data)
            
            return {"status": "success", "message": f"Added opportunity for {opportunity.get('site_name')}"}
        except Exception as e:
            print(f"Error inserting opportunity: {e}")
            return {"status": "error", "message": str(e)}
    
    def update_opportunity(self, site_url: str, updates: Dict) -> Dict:
        """Update an existing opportunity by URL"""
        if self.offline_mode or not self.worksheet:
            print(f"[OFFLINE] Would update opportunity for {site_url}")
            return {"status": "success", "message": "Offline mode - data not actually saved"}
            
        try:
            # Get all records
            all_records = self.worksheet.get_all_records()
            
            # Find the row with matching URL
            row_index = None
            for i, record in enumerate(all_records):
                if record['URL'] == site_url:
                    row_index = i + 2  # +2 because of header row and 0-indexing
                    break
            
            if not row_index:
                return {"status": "error", "message": f"No opportunity found with URL: {site_url}"}
            
            # Update specific cells
            for key, value in updates.items():
                if key in BACKLINK_COLUMNS:
                    col_index = BACKLINK_COLUMNS.index(key) + 1
                    self.worksheet.update_cell(row_index, col_index, value)
            
            return {"status": "success", "message": f"Updated opportunity for {site_url}"}
        except Exception as e:
            print(f"Error updating opportunity: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_all_opportunities(self) -> List[Dict]:
        """Get all opportunities from the spreadsheet"""
        if self.offline_mode or not self.worksheet:
            return [
                {
                    "Date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "Site Name": "example.com",
                    "URL": "https://example.com/write-for-us",
                    "Email": "editor@example.com",
                    "Status": "pending"
                }
            ]
            
        try:
            return self.worksheet.get_all_records()
        except Exception as e:
            print(f"Error getting opportunities: {e}")
            return []
    
    def get_opportunities_for_followup(self) -> List[Dict]:
        """Get opportunities that need follow-up"""
        if self.offline_mode or not self.worksheet:
            return []
            
        try:
            all_records = self.worksheet.get_all_records()
            
            # Filter for opportunities that:
            # 1. Have been emailed
            # 2. Haven't received a response
            # 3. Follow-up date is today or earlier, or empty and sent more than 7 days ago
            today = datetime.now().strftime('%Y-%m-%d')
            
            followup_opportunities = []
            for record in all_records:
                email_status = record.get('Email Status')
                if email_status == 'success':
                    followup_date = record.get('Follow-up Date', '')
                    response = record.get('Response Summary', '')
                    
                    # Empty response and either:
                    # - Has followup date that's today or earlier
                    # - Doesn't have followup date but was sent 7+ days ago
                    if not response and (
                        (followup_date and followup_date <= today) or
                        (not followup_date and 
                         record.get('Email Sent At') and 
                         (datetime.now() - datetime.fromisoformat(record.get('Email Sent At'))).days >= 7)
                    ):
                        followup_opportunities.append(record)
            
            return followup_opportunities
        except Exception as e:
            print(f"Error getting follow-up opportunities: {e}")
            return [] 