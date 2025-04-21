from flask import Blueprint, request, jsonify, current_app
from app.utils.email_service import send_welcome_email, send_password_reset_email
from app.utils.validation import validate_email
import traceback

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/welcome-email', methods=['POST'])
def send_welcome():
    print("\n=== Welcome Email Request ===")
    data = request.get_json()
    print(f"Request data: {data}")
    
    if not data or not data.get('email') or not data.get('name'):
        print("Error: Missing email or name")
        return jsonify({"message": "Email and name are required"}), 400
    
    email = data['email']
    name = data['name']
    
    # Validate email
    if not validate_email(email):
        print(f"Error: Invalid email format: {email}")
        return jsonify({"message": "Invalid email format"}), 400
    
    try:
        print(f"Sending welcome email to {email}")
        send_welcome_email(email, name)
        print("Welcome email sent successfully")
        return jsonify({"message": "Welcome email sent successfully"}), 200
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
        print(traceback.format_exc())
        current_app.logger.error(f"Error sending welcome email: {str(e)}")
        return jsonify({"message": "Failed to send welcome email"}), 500

@notifications_bp.route('/password-reset', methods=['POST'])
def send_reset():
    print("\n=== Password Reset Email Request ===")
    data = request.get_json()
    print(f"Request data: {data}")
    
    if not data or not data.get('email'):
        print("Error: Missing email")
        return jsonify({"message": "Email is required"}), 400
    
    email = data['email']
    name = data.get('name', None)  # Name is optional
    
    # Validate email
    if not validate_email(email):
        print(f"Error: Invalid email format: {email}")
        return jsonify({"message": "Invalid email format"}), 400
    
    try:
        print(f"Sending password reset email to {email}")
        verification_code = data.get('verification_code')
        if verification_code:
            print(f"Using provided verification code: {verification_code}")
        
        send_password_reset_email(email, name)
        print("Password reset email sent successfully")
        return jsonify({"message": "Password reset email sent successfully"}), 200
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        print(traceback.format_exc())
        current_app.logger.error(f"Error sending password reset email: {str(e)}")
        return jsonify({"message": "Failed to send password reset email"}), 500 