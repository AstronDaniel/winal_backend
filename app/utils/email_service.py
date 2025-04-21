import os
import random
import string
from datetime import datetime, timedelta
from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, HtmlContent
from app import db

# In a production environment, load this from environment variables
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', 'YOUR_SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@winaldrugshop.com')
FROM_NAME = os.getenv('FROM_NAME', 'Winal Drug Shop')

# Dictionary to store verification codes (in production, use database)
verification_codes = {}

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
        
        try:
            # If we're in development or testing mode, just print the email
            if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('TESTING'):
                print("\n=== PASSWORD RESET EMAIL (DEV MODE) ===")
                print(f"To: {email}")
                print(f"Subject: Password Reset - Winal Drug Shop")
                print(f"Verification Code: {code}")
                print("====================================\n")
                return True
                
            # Create email message
            message = Mail(
                from_email=Email(FROM_EMAIL, FROM_NAME),
                to_emails=To(email),
                subject="Password Reset - Winal Drug Shop",
                plain_text_content=Content("text/plain", plain_content),
                html_content=HtmlContent(html_content)
            )
            
            # Send email via SendGrid
            try:
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                response = sg.send(message)
                print(f"Password reset email sent to {email}, status code: {response.status_code}")
                if hasattr(current_app, 'logger'):
                    current_app.logger.info(f"Password reset email sent to {email}, status code: {response.status_code}")
            except Exception as e:
                print(f"SendGrid error: {str(e)}, falling back to console logging")
                if hasattr(current_app, 'logger'):
                    current_app.logger.warning(f"SendGrid error: {str(e)}, falling back to console logging")
                # Log the email content if SendGrid fails (for development)
                print("\n=== PASSWORD RESET EMAIL (CONSOLE FALLBACK) ===")
                print(f"To: {email}")
                print(f"Subject: Password Reset - Winal Drug Shop")
                print(f"Verification Code: {code}")
                print("====================================\n")
            
            return True
        except Exception as e:
            print(f"Error sending password reset email: {str(e)}")
            if hasattr(current_app, 'logger'):
                current_app.logger.error(f"Error sending password reset email: {str(e)}")
            raise
    except Exception as e:
        print(f"Global error in send_password_reset_email: {str(e)}")
        if hasattr(current_app, 'logger'):
            current_app.logger.error(f"Global error in send_password_reset_email: {str(e)}")
        raise

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
    
    try:
        # Create email message
        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(email),
            subject="Welcome to Winal Drug Shop!",
            plain_text_content=Content("text/plain", plain_content),
            html_content=HtmlContent(html_content)
        )
        
        # Send email via SendGrid
        try:
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)
            current_app.logger.info(f"Welcome email sent to {email}, status code: {response.status_code}")
        except Exception as e:
            current_app.logger.warning(f"SendGrid error: {str(e)}, falling back to console logging")
            # Log the email content if SendGrid fails (for development)
            print("\n=== WELCOME EMAIL (CONSOLE FALLBACK) ===")
            print(f"To: {email}")
            print(f"Subject: Welcome to Winal Drug Shop!")
            print(f"Name: {user_name}")
            print("====================================\n")
            
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending welcome email: {str(e)}")
        raise 