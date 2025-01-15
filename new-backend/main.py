from flask import Flask , jsonify , request
import requests
import json
import random
import smtplib
import string
from email.mime.text import MIMEText
from google.oauth2 import id_token
from google.auth.transport import requests
import psycopg2
import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
def otp_generate():
    otp = random.randint(1000 , 9999)
    return otp 
app = Flask(__name__)
   
DB_CONFIG = {
    "dbname": "credential",
    "user": "postgres",
    "password": "mysecretpassword",
    "host": "127.0.0.1",  # Use "postgres" if running in Docker container
    "port": 5432
}
 # Store OTP with 5-minute TTL



def connect_to_db():
    """Establish a connection to the PostgreSQL database."""
    return psycopg2.connect(**DB_CONFIG)    

def generate_random_alpha_code():
    return ''.join(random.choices(string.ascii_letters, k=16))

def smtp(text,email):
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    USERNAME = 'alaotach@gmail.com'
    PASSWORD = 'ayrh omvs mcsy kvdc'
    TO_EMAIL = email

    #  Create the email content
    subject = "Test Email"
    body = f"The otp for your login is {text}"
    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = USERNAME
    message['To'] = TO_EMAIL

    try:
    # Connect to the SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Upgrade to secure connection
            server.login(USERNAME, PASSWORD)  # Authenticate
            server.sendmail(USERNAME, TO_EMAIL, message.as_string())  # Send the email
            print("Email sent successfully!")
    except Exception as e:
        print("Failed to send email:", str(e))
    
GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID"

@app.route('/api/google-login', methods=['POST'])
def google_login():
    try:
        # Extract token from the request
        token = request.json.get('token')

        # Verify the token
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)

        # Get user info
        user_id = idinfo['sub']  # Google's unique ID for the user
        email = idinfo['email']
        name = idinfo['name']

        # Example response
        return jsonify({
            "status": "success",
            "user_id": user_id,
            "email": email,
            "name": name,
        })
    except ValueError as e:
        return jsonify({"error": "Invalid token", "details": str(e)}), 400

def check_code(email , passwd):
    try:
        # Connect to the database
        conn = connect_to_db()
        cursor = conn.cursor()
        code = generate_random_alpha_code()
        print("connected")

        # Example query (replace with your actual query)
        query = f"SELECT * FROM users WHERE user_id LIKE '{code}';"

        cursor.execute(query)
        print("executing select command")

        # Fetch the data
        results = cursor.fetchall()
        
        if results:
            print(f"User with code {code} already exists.")
            return jsonify({"error": "User already exists", "details": "User with this code already exists"}), 400
        
        else:
            query = f"INSERT INTO users(user_id,email,passwd,created_at ) VALUES ('{code}', '{email}','{passwd}',CURRENT_TIMESTAMP);" 
            cursor.execute(query)
            conn.commit()
            print("executed")
            return jsonify({"message":"added user"})
        

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()
def login(email , passwd):
    try:
        # Connect to the database
        conn = connect_to_db()
        cursor = conn.cursor()
        print("step 1")

        # Example query (replace with your actual query)
        query = f"SELECT user_id  FROM users WHERE email = '{email}' AND passwd = '{passwd}';"
        cursor.execute(query)
        print("executing select command")
        # Fetch the data
        result = cursor.fetchone()
        print("data taken")
        if result:
            return result[0]  # Return the value from the third column (age)
        else:
            return jsonify({"message":"invalid email or password"})
        cursor.close()
        conn.close()
    except:
        return jsonify({"error": "internal error"}), 401

@app.route("/otp", methods=["POST"])
def otp():
    try:
        data = request.get_json()  # Flask handles request objects automatically
        email = data.get('text', None)
        if not email:
            return jsonify({"error": "Missing email in request"}), 400

        generated_otp = otp_generate()
        r.setex(f"otp:{email}", 300, generated_otp) 
        smtp(generated_otp, email)
        otp = generated_otp + 0 
        return jsonify({f"message": "OTP sent successfully"}), 200 
    except Exception as e:
        return jsonify({"error": "An error occurred", "details": str(e)}), 500
    
@app.route("/auth", methods=['POST'])
def auth():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
        daata = data.get('text', None)
        email = data.get('email',None)
        stored_otp = r.get(f"otp:{email}")
        
        if stored_otp == daata:
            response_message = "AUTHENTICATION SUCCESSFUL"
            return response_message
        else:
            response_message = "AUTHENTICATION FAILURE: WRONG OTP"
                
            return response_message
        return jsonify({"message": response_message}), 200

    except Exception as e:
        return jsonify({"error": "An error occurred", "details": str(e)}), 500

    
    return "Auth Success"
    

@app.route('/signup', methods=['POST'])
def credentials():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
        email = data.get('email')
        passwd = data.get('passwd')
        check_code(email,passwd)
        return jsonify({"message": "Signup Success"}), 200    
    except:
        
        return jsonify({"message":"signup failed"}),200 
    
@app.route("/login", methods=["POST"])
def loged():    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON or no data provided"}), 400
        email = data.get('email')
        passwd = data.get('passwd')
        a = login(email,passwd)
        return a 
    except:
        return jsonify({"message":"Failure"})

 
if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True)
