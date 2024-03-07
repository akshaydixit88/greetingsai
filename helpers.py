import csv
import random
import string
import datetime
import pytz
import requests
import urllib
import uuid
from zxcvbn import zxcvbn 
import re
from openai import OpenAI
import os
from flask import redirect, render_template, session, Flask, send_from_directory, url_for
from functools import wraps


app = Flask(__name__)

# Specify the directory where you want to store the images
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function




def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"



def is_strong_password(password):
    """Check if the password is strong enough"""
    result = zxcvbn(password)
    return result['score'] >= 3


def is_valid_email(email):
    """Check if the email is valid"""
    email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")
    return bool(re.match(email_regex, email))



client = OpenAI(
  api_key='DEFAULT',  # this is also the default, it can be omitted
)


def generate_message(name, occasion, message_type, relation):
    
    prompt = f"Create a greeting message based on below instructions \\n 1. This greeting is for {name} by {relation} \\n2. The occasion being celebrated is {occasion}\\n 3. The tone of the message should be {message_type}\\n 4. The message should be between 4 to 6 lines. No more than 6 lines \\n 5. Split the message into 2-3 paragraphs \\n 6. Do not include salutation and title. Only message body\\n"
    # Call OpenAI GPT-3.5 Turbo to generate the story
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # You can adjust the engine as needed
        messages=[{"role": "system","content": "You are a greeting card writer for greeting card company like Hallmark Cards"},{"role": "user","content": prompt}],
        temperature=0.9,
  max_tokens=250,
  top_p=1,
  frequency_penalty=0,
  presence_penalty=0
    )

    # Extract the generated story from the OpenAI response
    generated_message = response.choices[0].message.content.strip()
    return generated_message



def generate_image(occasion, pictype, piccontext):
   
    prompt_i = f"Create a greeting card picture for {occasion}. Picture style {pictype}. Context for the picture {piccontext}. There should be no text in the image. "

    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt_i,
        size="1024x1024",
        quality="standard",
        n=1,
    )

    image_url = response.data[0].url
    return image_url



# Helper function to generate a random reset token
def generate_reset_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


#Code to save images

def save_image_from_url(image_url):
    try:
        # Download the image from the provided URL
        response = requests.get(image_url)
        response.raise_for_status()

        # Generate a unique filename based on the unique identifier
        unique_identifier = str(uuid.uuid4())
        filename = f"image_{unique_identifier}.png"  
        UPLOAD_FOLDER = '/static/images'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save the image to the specified directory
        with open(file_path, 'wb') as f:
            f.write(response.content)

        # Return the filename pointing to the saved image
        
        return filename

    except Exception as e:
        # Handle errors, e.g., invalid URL or failed download
        print(f"Error: {e}")
        return None
