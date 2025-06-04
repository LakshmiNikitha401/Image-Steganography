from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_socketio import SocketIO, emit
import os
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from PIL import Image
import numpy as np
import time
import struct
import hashlib

app = Flask(__name__, template_folder=os.path.join(os.getcwd(), 'templates'))
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

# Configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
EXTRACTED_FOLDER = os.path.join(os.getcwd(), 'extracted')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)
COVER_IMAGE_MIN_SIZE = 100 * 1024  # 100KB minimum cover image size

# OTP Storage
otp_store = {}

def generate_otp():
    otp = str(random.randint(1000, 9999))  # 6-digit OTP
    otp_store[otp] = time.time() + 3600  # 1 hour expiry
    return otp

def is_otp_valid(otp):
    return otp in otp_store and time.time() < otp_store[otp]

def send_otp_email(receiver_email, stego_path):
    try:
        otp = generate_otp()
        msg = MIMEMultipart()
        msg['From'] = 'imagesteganography24@gmail.com'
        msg['To'] = receiver_email
        msg['Subject'] = 'Your Steganography OTP'
        
        body = f"Your OTP is: {otp}\nValid for 1 hour."
        msg.attach(MIMEText(body, 'plain'))

        with open(stego_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename=stego_image.png')
            msg.attach(part)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login('imagesteganography24@gmail.com', "iarx bipf iyvg iehi")
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def calculate_capacity(image_path):
    img = Image.open(image_path)
    return (img.size[0] * img.size[1] * 3) // 8  # Capacity in bytes

def hide_data(cover_path, secret_path, output_path):
    try:
        # Read and prepare secret data
        with open(secret_path, 'rb') as f:
            secret_data = f.read()
        
        # Create robust header: [4B magic][4B size][32B hash][1B type][data]
        header = b'STEG'  # Magic number
        header += struct.pack('>I', len(secret_data))  # Data size
        header += hashlib.sha256(secret_data).digest()  # Hash
        header += bytes([get_file_type_code(secret_path)])  # File type
        
        full_data = header + secret_data
        
        # Convert to binary string
        binary_data = ''.join(f'{byte:08b}' for byte in full_data)
        
        # Embed in image
        img = Image.open(cover_path)
        pixels = np.array(img)
        flat = pixels.reshape(-1)
        
        if len(binary_data) > len(flat):
            raise ValueError("Data too large for cover image")
        
        # Embed data in LSBs
        for i in range(len(binary_data)):
            flat[i] = (flat[i] & 0xFE) | int(binary_data[i])
        
        # Save stego image
        Image.fromarray(flat.reshape(pixels.shape)).save(output_path)
        return True
    except Exception as e:
        print(f"Hiding error: {e}")
        return False

def extract_data(stego_path, output_base):
    try:
        img = Image.open(stego_path)
        flat = np.array(img).reshape(-1)
        
        # Extract binary data
        binary = ''.join(str(pixel & 1) for pixel in flat)
        
        # Convert to bytes
        data = bytearray()
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            if len(byte) == 8:
                data.append(int(byte, 2))
        
        # Parse header
        if len(data) < 41:  # 4B magic + 4B size + 32B hash + 1B type
            raise ValueError("Incomplete header")
        
        if data[:4] != b'STEG':
            raise ValueError("Invalid stego file")
        
        size = struct.unpack('>I', data[4:8])[0]
        expected_hash = data[8:40]
        file_type = data[40]
        file_data = data[41:41+size]
        
        if len(file_data) != size:
            raise ValueError("Size mismatch")
        
        if hashlib.sha256(file_data).digest() != expected_hash:
            raise ValueError("Data corrupted")
        
        # Determine extension
        ext = get_extension_from_code(file_type)
        output_path = f"{output_base}{ext}"
        
        # Save extracted file
        with open(output_path, 'wb') as f:
            f.write(file_data)
        
        return True
    except Exception as e:
        print(f"Extraction error: {e}")
        return False

def get_file_type_code(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return {
        '.txt': 0, '.text': 0,
        '.png': 1, '.jpg': 1, '.jpeg': 1, '.gif': 1,
        '.mp3': 2, '.wav': 2, '.ogg': 2,
        '.mp4': 3, '.avi': 3, '.mov': 3
    }.get(ext, 0)

def get_extension_from_code(code):
    return ['.txt', '.png', '.mp3', '.mp4'][code] if 0 <= code <= 3 else '.bin'

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hide', methods=['GET', 'POST'])
def hide():
    if request.method == 'POST':
        try:
            # Validate input
            if 'cover_image' not in request.files or 'hidden_file' not in request.files:
                flash("Missing files")
                return redirect(url_for('hide'))
            
            cover = request.files['cover_image']
            secret = request.files['hidden_file']
            email = request.form.get('email', '')
            
            if not email or not cover.filename or not secret.filename:
                flash("All fields are required")
                return redirect(url_for('hide'))
            
            # Save files
            timestamp = str(int(time.time()))
            cover_path = os.path.join(UPLOAD_FOLDER, f"cover_{timestamp}.png")
            secret_path = os.path.join(UPLOAD_FOLDER, f"secret_{timestamp}{os.path.splitext(secret.filename)[1]}")
            output_path = os.path.join(UPLOAD_FOLDER, f"stego_{timestamp}.png")
            
            cover.save(cover_path)
            secret.save(secret_path)
            
            # Check capacity
            secret_size = os.path.getsize(secret_path)
            capacity = calculate_capacity(cover_path)
            
            if secret_size > capacity:
                flash(f"File too large (needs {secret_size/1024:.1f}KB, capacity {capacity/1024:.1f}KB)")
                return redirect(url_for('hide'))
            
            # Hide data
            if not hide_data(cover_path, secret_path, output_path):
                flash("Error hiding data")
                return redirect(url_for('hide'))
            
            # Send email
            if not send_otp_email(email, output_path):
                flash("Error sending OTP email")
                return redirect(url_for('hide'))
            
            flash("Success! Check your email for the OTP.")
            return redirect(url_for('thank_you'))
        except Exception as e:
            print(f"Error in hide: {e}")
            flash("An error occurred")
            return redirect(url_for('hide'))
    return render_template('hide.html')

@app.route('/extract', methods=['GET', 'POST'])
def extract():
    if request.method == 'POST':
        otp = request.form.get('otp', '')
        if is_otp_valid(otp):
            return redirect(url_for('extract_data_type'))
        flash("Invalid or expired OTP")
    return render_template('extract.html')

@app.route('/extract_data_type', methods=['GET', 'POST'])
def extract_data_type():
    if request.method == 'POST':
        try:
            if 'stego_image' not in request.files:
                flash("No file uploaded")
                return redirect(url_for('extract_data_type'))
            
            stego = request.files['stego_image']
            if not stego.filename:
                flash("No file selected")
                return redirect(url_for('extract_data_type'))
            
            # Save stego image
            timestamp = str(int(time.time()))
            stego_path = os.path.join(EXTRACTED_FOLDER, f"stego_{timestamp}.png")
            output_base = os.path.join(EXTRACTED_FOLDER, f"extracted_{timestamp}")
            
            stego.save(stego_path)
            
            # Extract data
            if not extract_data(stego_path, output_base):
                flash("Extraction failed")
                return redirect(url_for('extract_data_type'))
            
            # Find the extracted file
            for f in os.listdir(EXTRACTED_FOLDER):
                if f.startswith(f"extracted_{timestamp}"):
                    return redirect(url_for('download_file', filename=f))
            
            flash("Extracted file not found")
            return redirect(url_for('extract_data_type'))
        except Exception as e:
            print(f"Error in extraction: {e}")
            flash("Extraction error")
            return redirect(url_for('extract_data_type'))
    return render_template('extract_data_type.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(EXTRACTED_FOLDER, filename, as_attachment=True)
    except Exception as e:
        print(f"Download error: {e}")
        flash("Download failed")
        return redirect(url_for('extract_data_type'))

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)