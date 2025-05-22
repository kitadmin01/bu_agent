"""
Email provider abstraction for the backlink agent
"""
import os
import smtplib
import imaplib
import email
import asyncio
import random
import uuid
from typing import Dict, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from dotenv import load_dotenv
from browser_use import Agent
from langchain_openai import ChatOpenAI

load_dotenv()

class EmailProvider:
    """Abstraction layer for different email sending methods"""
    
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("EMAIL_PROVIDER", "smtp")
        self.offline_mode = True
        self.agent = self._setup_agent()
        
        # Email Server Configuration
        self.email_config = {
            # SMTP Configuration
            "smtp_host": os.getenv("SMTP_HOST", "secure.emailsrvr.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", 465)),
            "smtp_use_ssl": os.getenv("SMTP_USE_SSL", "true").lower() == "true",
            
            # IMAP Configuration
            "imap_host": os.getenv("IMAP_HOST", "secure.emailsrvr.com"),
            "imap_port": int(os.getenv("IMAP_PORT", 993)),
            "imap_use_ssl": os.getenv("IMAP_USE_SSL", "true").lower() == "true",
            
            # Authentication
            "username": os.getenv("EMAIL_USERNAME"),
            "password": os.getenv("EMAIL_PASSWORD"),
        }
        
        # Email settings
        self.from_email = os.getenv("FROM_EMAIL", self.email_config["username"])
        self.from_name = os.getenv("FROM_NAME", "AnalyticKit Team")
        self.email_delay = int(os.getenv("EMAIL_DELAY", "1"))
    
    def _setup_agent(self):
        """Set up browser-use agent with proper error handling"""
        try:
            # Import browser-use and langchain
            from browser_use import Agent
            from langchain_openai import ChatOpenAI
            
            # Try with LLMProvider
            try:
                from utils.llm_provider import LLMProvider
                llm_provider = LLMProvider()
                agent = Agent(
                    task="Web form automation",
                    llm=llm_provider.get_llm()
                )
                self.offline_mode = False
                return agent
            except Exception as e:
                print(f"Warning: Error initializing browser-use Agent with LLM provider: {e}")
                print("Trying direct OpenAI initialization...")
                
                # Try direct OpenAI
                try:
                    openai_api_key = os.getenv("OPENAI_API_KEY")
                    if not openai_api_key:
                        raise ValueError("OPENAI_API_KEY environment variable is required")
                    
                    llm = ChatOpenAI(
                        api_key=openai_api_key,
                        model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
                    )
                    agent = Agent(
                        task="Web form automation",
                        llm=llm
                    )
                    self.offline_mode = False
                    return agent
                except Exception as e2:
                    print(f"Warning: Direct OpenAI initialization also failed: {e2}")
                    print("Falling back to offline mode...")
                    self.offline_mode = True
                    return None
                    
        except ImportError as e:
            print(f"Warning: browser-use library not available: {e}")
            print("Using offline mode for email operations")
            self.offline_mode = True
            return None
        except Exception as e:
            print(f"Warning: Unexpected error initializing browser-use: {e}")
            print("Using offline mode for email operations")
            self.offline_mode = True
            return None

    async def send_email(self, to_email: str, subject: str, message: str, 
                        form_url: Optional[str] = None) -> Dict:
        """Send email using the appropriate method"""
        if self.offline_mode:
            return self._offline_send_email(to_email, subject, form_url)
            
        if form_url and self.provider == "web_form":
            return await self.send_via_web_form(form_url, subject, message)
        elif to_email and self.provider == "smtp":
            return await self.send_via_smtp(to_email, subject, message)
        else:
            # Try web form first, then SMTP
            if form_url:
                result = await self.send_via_web_form(form_url, subject, message)
                if result["status"] == "success":
                    return result
            
            if to_email:
                return await self.send_via_smtp(to_email, subject, message)
            
            return {"status": "no_contact", "message": "No contact method available"}
    
    def _offline_send_email(self, to_email: str, subject: str, form_url: Optional[str] = None) -> Dict:
        """Simulate sending email in offline mode"""
        method = "web_form" if form_url else "smtp"
        contact = form_url if form_url else to_email
        
        print(f"[OFFLINE] Sending email via {method} to: {contact}")
        print(f"[OFFLINE] Subject: {subject}")
        
        return {
            "status": "success",
            "method": method,
            "url": form_url,
            "email": to_email,
            "timestamp": datetime.now().isoformat(),
            "offline": True
        }
    
    async def send_via_web_form(self, form_url: str, subject: str, message: str) -> Dict:
        """Send email through web form"""
        if self.offline_mode or not self.agent:
            return self._offline_send_email(None, subject, form_url)
            
        try:
            result = await self.agent.run(f"""
                Visit {form_url} and fill out the contact/submission form with:
                
                Subject/Title: {subject}
                Message/Content: {message}
                Email: {self.from_email}
                Name: {self.from_name}
                
                Look for common form fields like:
                - Subject, Title, or Topic
                - Message, Content, or Description  
                - Email or Contact Email
                - Name or Full Name
                
                Submit the form after filling it out.
                Return the status as a dictionary with 'submitted' key.
            """)
            
            await asyncio.sleep(self.email_delay)
            
            return {
                "status": "success" if result.get("submitted") else "failed",
                "method": "web_form",
                "url": form_url,
                "timestamp": datetime.now().isoformat(),
                "details": result
            }
            
        except Exception as e:
            print(f"Web form error: {e}")
            print("Falling back to offline mode")
            return self._offline_send_email(None, subject, form_url)
    
    async def send_via_smtp(self, to_email: str, subject: str, message: str) -> Dict:
        """Send email via SMTP"""
        try:
            # Run SMTP in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp_email, to_email, subject, message)
            
            await asyncio.sleep(self.email_delay)
            
            return {
                "status": "success",
                "method": "smtp",
                "email": to_email,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "method": "smtp",
                "email": to_email,
                "timestamp": datetime.now().isoformat()
            }
    
    def _send_smtp_email(self, to_email: str, subject: str, message: str):
        """Send email via SMTP (synchronous)"""
        msg = MIMEMultipart()
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'plain'))
        
        # Use SSL connection for secure.emailsrvr.com
        if self.email_config['smtp_use_ssl']:
            with smtplib.SMTP_SSL(self.email_config['smtp_host'], self.email_config['smtp_port']) as server:
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.email_config['smtp_host'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)
    
    async def check_for_replies(self, days: int = 7) -> List[Dict]:
        """Check for email replies using IMAP"""
        try:
            # Run IMAP in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            replies = await loop.run_in_executor(None, self._check_imap_emails, days)
            return replies
        except Exception as e:
            print(f"Error checking emails: {e}")
            return []
    
    def _check_imap_emails(self, days: int = 7) -> List[Dict]:
        """Check emails via IMAP (synchronous)"""
        replies = []
        
        try:
            # Connect to IMAP server
            if self.email_config['imap_use_ssl']:
                mail = imaplib.IMAP4_SSL(self.email_config['imap_host'], self.email_config['imap_port'])
            else:
                mail = imaplib.IMAP4(self.email_config['imap_host'], self.email_config['imap_port'])
            
            # Login
            mail.login(self.email_config['username'], self.email_config['password'])
            
            # Select inbox
            mail.select('INBOX')
            
            # Search for emails in the last X days
            from_date = (datetime.now() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
            status, messages = mail.search(None, f'(SINCE {from_date})')
            
            if status == 'OK':
                for num in messages[0].split():
                    status, data = mail.fetch(num, '(RFC822)')
                    if status == 'OK':
                        email_msg = email.message_from_bytes(data[0][1])
                        
                        # Extract email details
                        subject = email_msg['subject']
                        from_email = email_msg['from']
                        date = email_msg['date']
                        
                        # Get email body
                        body = ""
                        if email_msg.is_multipart():
                            for part in email_msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = email_msg.get_payload(decode=True).decode()
                        
                        replies.append({
                            'id': num.decode(),
                            'from': from_email,
                            'subject': subject,
                            'date': date,
                            'body': body,
                            'is_read': 'Seen' in mail.fetch(num, '(FLAGS)')[1][0].decode()
                        })
            
            # Logout
            mail.logout()
            
            return replies
        
        except Exception as e:
            print(f"IMAP error: {e}")
            return []
    
    def mark_email_as_read(self, email_id: str) -> bool:
        """Mark an email as read"""
        try:
            # Connect to IMAP server
            if self.email_config['imap_use_ssl']:
                mail = imaplib.IMAP4_SSL(self.email_config['imap_host'], self.email_config['imap_port'])
            else:
                mail = imaplib.IMAP4(self.email_config['imap_host'], self.email_config['imap_port'])
            
            # Login
            mail.login(self.email_config['username'], self.email_config['password'])
            
            # Select inbox
            mail.select('INBOX')
            
            # Mark as read
            mail.store(email_id, '+FLAGS', '\\Seen')
            
            # Logout
            mail.logout()
            
            return True
        except Exception as e:
            print(f"Error marking email as read: {e}")
            return False
    
    def generate_guest_post_email(self, site_name: str, guidelines: str = "") -> Dict:
        """Generate a personalized guest post email"""
        subject = f"Guest Post Proposal - Web3 Marketing Content for {site_name}"
        
        message = f"""Dear {site_name} Team,

        I hope this email finds you well. I'm reaching out to propose a guest post for your website.

        I specialize in Web3 and blockchain marketing, and I believe I could provide valuable content
        for your audience. I have extensive experience in DeFi marketing strategies, NFT promotion,
        and blockchain technology adoption.

        Some topics I could cover include:
        - Web3 Marketing Best Practices
        - DeFi User Acquisition Strategies  
        - NFT Marketing and Community Building
        - Blockchain Technology Adoption in Traditional Business
        - Crypto Brand Development and Positioning

        {f"I've reviewed your guest post guidelines and understand your requirements." if guidelines else ""}

        I would be happy to provide a detailed outline and samples of my previous work if you're interested.

        Thank you for your time and consideration.

        Best regards,
        {self.from_name}
        {self.from_email}
        """
        
        return {"subject": subject, "message": message} 