import os
import base64
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import current_app
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import random
import string

# If modifying these SCOPES, delete the token.pickle file
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

# Dictionary to store verification codes (in production, use database)
verification_codes = {}

# Email configuration
FROM_EMAIL = os.getenv('GMAIL_SENDER', 'astrondaniel6@gmail.com')
FROM_NAME = os.getenv('GMAIL_SENDER_NAME', 'Winal Drug Shop')

def get_gmail_service():
    """Get Gmail API service instance."""
    credentials = None
    token_path = os.path.join(os.environ.get('FLASK_ROOT', '.'), 'token.pickle')
    credentials_path = os.path.join(os.environ.get('FLASK_ROOT', '.'), 'credentials.json')
    
    # Check if token.pickle exists
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            credentials = pickle.load(token)
    
    # If credentials don't exist or are invalid
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # If credentials.json doesn't exist, log error
            if not os.path.exists(credentials_path):
                print(f"Error: credentials.json not found at {credentials_path}")
                current_app.logger.error(f"credentials.json not found at {credentials_path}")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            credentials = flow.run_local_server(port=0)
            
        # Save the credentials for next run
        with open(token_path, 'wb') as token:
            pickle.dump(credentials, token)
    
    # Build Gmail service
    try:
        service = build('gmail', 'v1', credentials=credentials)
        return service
    except Exception as e:
        print(f"Error building Gmail service: {str(e)}")
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Error building Gmail service: {str(e)}")
        return None

def generate_verification_code(length=6):
    """Generate a random verification code"""
    return ''.join(random.choices(string.digits, k=length))

def store_verification_code(email, code, expiry_minutes=15):
    """Store verification code with expiration"""
    try:
        # Calculate expiration time
        expiry_time = datetime.utcnow() + timedelta(minutes=expiry_minutes)
        
        # Store code with expiry
        verification_codes[email] = {
            'code': code,
            'expires_at': expiry_time
        }
        
        # Print for debugging
        print(f"Stored verification code for {email}: {code}, expires at {expiry_time}")
        return True
    except Exception as e:
        print(f"Error storing verification code: {str(e)}")
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Error storing verification code: {str(e)}")
        return False

def verify_code(email, code):
    """Verify a code for an email"""
    if email not in verification_codes:
        return False
        
    stored_data = verification_codes[email]
    if stored_data['expires_at'] < datetime.utcnow():
        # Code has expired
        del verification_codes[email]
        return False
        
    if stored_data['code'] != code:
        return False
        
    return True

def clear_verification_code(email):
    """Clear a verification code after use"""
    if email in verification_codes:
        del verification_codes[email]
        
def send_email(to, subject, html_content, text_content=None):
    """Send an email using Gmail API"""
    try:
        # Get Gmail service
        service = get_gmail_service()
        if not service:
            print("Failed to get Gmail service")
            return False
            
        # Create message
        message = MIMEMultipart('alternative')
        message['to'] = to
        message['subject'] = subject
        
        # Set From header with name and email
        message['from'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        
        # Attach parts
        if text_content:
            part1 = MIMEText(text_content, 'plain')
            message.attach(part1)
            
        part2 = MIMEText(html_content, 'html')
        message.attach(part2)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send message
        try:
            message = service.users().messages().send(
                userId='me', body={'raw': raw_message}).execute()
            print(f"Email sent to {to}, message ID: {message.get('id')}")
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Error sending email: {str(e)}")
            
            # For development, log the email content
            print("\n=== EMAIL (GMAIL ERROR) ===")
            print(f"To: {to}")
            print(f"Subject: {subject}")
            print("====================================\n")
            return False
            
    except Exception as e:
        print(f"Error in send_email: {str(e)}")
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Error in send_email: {str(e)}")
        return False

def send_password_reset_email(email, name=None):
    """Send password reset email with verification code"""
    try:
        # Generate verification code
        code = generate_verification_code()
        print(f"Generated verification code for {email}: {code}")
        
        # Store in memory dictionary
        if not store_verification_code(email, code):
            error_msg = "Failed to store verification code"
            print(error_msg)
            raise Exception(error_msg)
        
        # Format name
        user_name = name if name else "Valued Customer"
        
        # Create email content
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
          <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #2196F3;">Winal Drug Shop</h2>
          </div>
          <div>
            <h3>Password Reset</h3>
            <p>Dear {user_name},</p>
            <p>You requested a password reset for your Winal Drug Shop account.</p>
            <p>Your verification code is:</p>
            <div style="background-color: #f5f5f5; padding: 15px; text-align: center; font-size: 24px; letter-spacing: 5px; border-radius: 5px; margin: 20px 0;">
              <strong>{code}</strong>
            </div>
            <p>This code will expire in 15 minutes.</p>
            <p>If you did not request a password reset, please ignore this email or contact our support team if you have concerns.</p>
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
            <p style="font-size: 12px; color: #757575; text-align: center;">
              &copy; {datetime.now().year} Winal Drug Shop. All rights reserved.
            </p>
          </div>
        </div>
        """
        
        plain_content = f"""
        Password Reset - Winal Drug Shop
        
        Dear {user_name},
        
        You requested a password reset for your Winal Drug Shop account.
        
        Your verification code is: {code}
        
        This code will expire in 15 minutes.
        
        If you did not request a password reset, please ignore this email or contact our support team if you have concerns.
        
        © {datetime.now().year} Winal Drug Shop. All rights reserved.
        """
        
        # If we're in development or testing mode, just print the email
        if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('TESTING'):
            print("\n=== PASSWORD RESET EMAIL (DEV MODE) ===")
            print(f"To: {email}")
            print(f"Subject: Password Reset - Winal Drug Shop")
            print(f"Verification Code: {code}")
            print("====================================\n")
            return True
        
        # Send email
        return send_email(
            to=email,
            subject="Password Reset - Winal Drug Shop",
            html_content=html_content,
            text_content=plain_content
        )
        
    except Exception as e:
        print(f"Global error in send_password_reset_email: {str(e)}")
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Global error in send_password_reset_email: {str(e)}")
        return False

def send_welcome_email(email, name):
    """Send welcome email to newly registered user"""
    # Format name
    user_name = name if name else "Valued Customer"
    
    # Create email content
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
      <div style="text-align: center; margin-bottom: 20px;">
        <h2 style="color: #2196F3;">Winal Drug Shop</h2>
      </div>
      <div>
        <h3>Welcome to Winal Drug Shop!</h3>
        <p>Dear {user_name},</p>
        <p>Thank you for registering with Winal Drug Shop! Your account has been successfully created.</p>
        <p>With your new account, you can:</p>
        <ul>
          <li>Browse our wide range of animal and human medications</li>
          <li>Book appointments for farm activities and consultations</li>
          <li>Track your orders and prescription history</li>
          <li>Access exclusive health tips and resources</li>
        </ul>
        <p>If you have any questions or need assistance, please don't hesitate to contact us.</p>
        <p>Best regards,<br>The Winal Drug Shop Team</p>
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #e0e0e0;">
        <p style="font-size: 12px; color: #757575; text-align: center;">
          &copy; {datetime.now().year} Winal Drug Shop. All rights reserved.
        </p>
      </div>
    </div>
    """
    
    plain_content = f"""
    Welcome to Winal Drug Shop!
    
    Dear {user_name},
    
    Thank you for registering with Winal Drug Shop! Your account has been successfully created.
    
    With your new account, you can:
    • Browse our wide range of animal and human medications
    • Book appointments for farm activities and consultations
    • Track your orders and prescription history
    • Access exclusive health tips and resources
    
    If you have any questions or need assistance, please don't hesitate to contact us.
    
    Best regards,
    The Winal Drug Shop Team
    
    © {datetime.now().year} Winal Drug Shop. All rights reserved.
    """
    
    # If we're in development or testing mode, just print the email
    if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('TESTING'):
        print("\n=== WELCOME EMAIL (DEV MODE) ===")
        print(f"To: {email}")
        print(f"Subject: Welcome to Winal Drug Shop!")
        print("====================================\n")
        return True
    
    # Send email
    return send_email(
        to=email,
        subject="Welcome to Winal Drug Shop!",
        html_content=html_content,
        text_content=plain_content
    ) 