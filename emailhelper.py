from flask_mail import Mail, Message
from flask import Flask, url_for


# Create the Flask app
app = Flask(__name__)

# Create an instance of the Mail class
mail = Mail(app)

# Configure your email settings
app.config['MAIL_SERVER'] = 'smtp.your-email-provider.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'

# Send reset email function
def send_reset_email(to_email, reset_token):
    subject = "Password Reset Request"
    body = f"Click the following link to reset your password: {url_for('reset_password', reset_token=reset_token, _external=True)}"
    print(body)
    msg = Message(subject=subject, recipients=[to_email], body=body)
    mail.send(msg)