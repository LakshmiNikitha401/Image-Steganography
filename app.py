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
import io
import time
import numpy as np

# Initialize Flask app with correct template folder
app = Flask(__name__, template_folder=os.path.join(os.getcwd(), 'templates'))
app.secret_key = 'your_secret_key'
socketio = SocketIO(app, async_mode='gevent') 

# Configure folders for Render.com
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
EXTRACTED_FOLDER = os.path.join(os.getcwd(), 'extracted')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)

# In-memory store for OTPs
otp_store = {}

# Size constraints (in bytes)
COVER_IMAGE_MIN_SIZE = 1 * 1024  # 1 KB
def generate_otp():
    otp = str(random.randint(1000, 9999))
    expiry_time = time.time() + 24 * 3600  # OTP expires in 24 hours
    otp_store[otp] = expiry_time
    return otp

def is_otp_valid(otp):
    if otp in otp_store and time.time() < otp_store[otp]:
        return True
    return False

def send_otp_email(receiver_email, stego_image_path):
    try:
        otp = generate_otp()
        subject = "Image Steganography OTP and Stego Image"
        body = f'Welcome to Image Steganography. Here is your OTP for extracting data: "{otp}"\n\n'
        body += "The attached image contains the hidden data. Use the OTP to extract it."

        msg = MIMEMultipart()
        msg['From'] = 'imagesteganography24@gmail.com'
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Attach the stego image
        with open(stego_image_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(stego_image_path)}')
            msg.attach(part)

        # Send the email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login('imagesteganography24@gmail.com', "fgku cjzw uqev zkrl")
            server.sendmail('imagesteganography24@gmail.com', receiver_email, msg.as_string())
        print("Email sent successfully!")  # Debugging
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}")  # Debugging
        flash("Failed to authenticate with the email server. Please check your email credentials.")
        return False
    except smtplib.SMTPException as e:
        print(f"SMTP Error: {e}")  # Debugging
        flash("Failed to send email. Please check your internet connection or try again later.")
        return False
    except Exception as e:
        print(f"Unexpected Error: {e}")  # Debugging
        flash("Failed to send email. Please try again.")
        return False

def text_to_bits(text):
    return ''.join(format(ord(i), '08b') for i in text)

def bits_to_text(bits):
    chars = [bits[i:i+8] for i in range(0, len(bits), 8)]
    return ''.join(chr(int(char, 2)) for char in chars)

def get_image_bytes(image_path):
    with open(image_path, 'rb') as image_file:
        return image_file.read()

def get_audio_bytes(audio_path):
    with open(audio_path, 'rb') as audio_file:
        return audio_file.read()

def get_video_bytes(video_path):
    with open(video_path, 'rb') as video_file:
        return video_file.read()

def calculate_capacity(cover_image_path):
    cover_image = Image.open(cover_image_path)
    width, height = cover_image.size
    capacity_bits = width * height * 3  # 3 bits per pixel (RGB)
    capacity_bytes = capacity_bits // 8  # Convert bits to bytes
    capacity_kb = capacity_bytes / 1024  # Convert bytes to KB
    return capacity_kb

def hide_data_in_image(cover_image_path, hidden_file_path, output_image_path):
    try:
        cover_image = Image.open(cover_image_path)
        pixels = cover_image.load()
        with open(hidden_file_path, 'rb') as file:
            data = file.read()
        binary_data = ''.join(format(byte, '08b') for byte in data) + '1111111111111110'  # Add end marker
        width, height = cover_image.size
        binary_index = 0
        for y in range(height):
            for x in range(width):
                if binary_index < len(binary_data):
                    r, g, b = pixels[x, y]
                    r = (r & ~1) | int(binary_data[binary_index])
                    binary_index += 1
                    if binary_index < len(binary_data):
                        g = (g & ~1) | int(binary_data[binary_index])
                        binary_index += 1
                    if binary_index < len(binary_data):
                        b = (b & ~1) | int(binary_data[binary_index])
                        binary_index += 1
                    pixels[x, y] = (r, g, b)
                else:
                    break
        cover_image.save(output_image_path)
        print(f"Stego image saved successfully at {output_image_path}.")  # Debugging
        return True
    except Exception as e:
        print(f"Error hiding data: {e}")  # Debugging
        flash(f"Error hiding data: {e}")
        return False

def extract_data_from_image(stego_image_path, output_file_path):
    try:
        stego_image = Image.open(stego_image_path)
        pixels = stego_image.load()
        width, height = stego_image.size
        binary_data = ""
        total_pixels = width * height
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                binary_data += str(r & 1)
                binary_data += str(g & 1)
                binary_data += str(b & 1)
                if binary_data[-16:] == '1111111111111110':  # End marker
                    break
                # Emit progress update
                progress = int((y * width + x) / total_pixels * 100)
                socketio.emit('progress_update', {'progress': progress})  # Send progress to frontend
            else:
                continue
            break

        # Convert binary data to bytes
        extracted_bytes = bytearray()
        for i in range(0, len(binary_data[:-16]), 8):
            byte = binary_data[i:i+8]
            if len(byte) == 8:
                extracted_bytes.append(int(byte, 2))

        # Save the extracted data to a file
        with open(output_file_path, 'wb') as file:
            file.write(extracted_bytes)
        print(f"Extracted data saved successfully at {output_file_path}.")  # Debugging
        return True
    except Exception as e:
        print(f"Error extracting data: {e}")  # Debugging
        flash(f"Error extracting data: {e}")
        return False

def hide_image_in_image(cover_image_path, hidden_image_path, output_image_path):
    try:
        cover_image = Image.open(cover_image_path)
        hidden_image_bytes = get_image_bytes(hidden_image_path)
        binary_hidden_image = ''.join(format(byte, '08b') for byte in hidden_image_bytes) + '1111111111111110'  # Add end marker
        width, height = cover_image.size
        pixels = cover_image.load()
        binary_index = 0
        for y in range(height):
            for x in range(width):
                if binary_index < len(binary_hidden_image):
                    r, g, b = pixels[x, y]
                    r = (r & ~1) | int(binary_hidden_image[binary_index])
                    binary_index += 1
                    if binary_index < len(binary_hidden_image):
                        g = (g & ~1) | int(binary_hidden_image[binary_index])
                        binary_index += 1
                    if binary_index < len(binary_hidden_image):
                        b = (b & ~1) | int(binary_hidden_image[binary_index])
                        binary_index += 1
                    pixels[x, y] = (r, g, b)
                else:
                    break
        cover_image.save(output_image_path)
        print(f"Stego image saved successfully at {output_image_path}.")  # Debugging
        return True
    except Exception as e:
        print(f"Error hiding image: {e}")  # Debugging
        flash(f"Error hiding image: {e}")
        return False

def extract_image_from_image(stego_image_path, output_image_path):
    try:
        stego_image = Image.open(stego_image_path)
        binary_hidden_image = ""
        total_pixels = stego_image.width * stego_image.height
        pixel_count = 0
        for pixel in stego_image.getdata():
            r, g, b = pixel
            binary_hidden_image += str(r & 1)
            binary_hidden_image += str(g & 1)
            binary_hidden_image += str(b & 1)
            pixel_count += 1
            # Emit progress update
            progress = int((pixel_count / total_pixels) * 100)
            socketio.emit('progress_update', {'progress': progress})  # Send progress to frontend
        # Remove the end marker
        binary_hidden_image = binary_hidden_image[:-16]
        hidden_image_bytes = bytearray()
        for i in range(0, len(binary_hidden_image), 8):
            byte = binary_hidden_image[i:i+8]
            if len(byte) == 8:
                hidden_image_bytes.append(int(byte, 2))
        with open(output_image_path, 'wb') as image_file:
            image_file.write(hidden_image_bytes)
        print(f"Extracted image saved successfully at {output_image_path}.")  # Debugging
        return True
    except Exception as e:
        print(f"Error extracting image: {e}")  # Debugging
        flash(f"Error extracting image: {e}")
        return False

def hide_audio_in_image(cover_image_path, audio_path, output_image_path):
    try:
        cover_image = Image.open(cover_image_path)
        audio_bytes = get_audio_bytes(audio_path)
        binary_audio = ''.join(format(byte, '08b') for byte in audio_bytes) + '1111111111111110'  # Add end marker
        width, height = cover_image.size
        pixels = cover_image.load()
        binary_index = 0
        for y in range(height):
            for x in range(width):
                if binary_index < len(binary_audio):
                    r, g, b = pixels[x, y]
                    r = (r & ~1) | int(binary_audio[binary_index])
                    binary_index += 1
                    if binary_index < len(binary_audio):
                        g = (g & ~1) | int(binary_audio[binary_index])
                        binary_index += 1
                    if binary_index < len(binary_audio):
                        b = (b & ~1) | int(binary_audio[binary_index])
                        binary_index += 1
                    pixels[x, y] = (r, g, b)
                else:
                    break
        cover_image.save(output_image_path)
        print(f"Stego image saved successfully at {output_image_path}.")  # Debugging
        return True
    except Exception as e:
        print(f"Error hiding audio: {e}")  # Debugging
        flash(f"Error hiding audio: {e}")
        return False

def extract_audio_from_image(stego_image_path, output_audio_path):
    try:
        stego_image = Image.open(stego_image_path)
        binary_audio = ""
        total_pixels = stego_image.width * stego_image.height
        pixel_count = 0
        for pixel in stego_image.getdata():
            r, g, b = pixel
            binary_audio += str(r & 1)
            binary_audio += str(g & 1)
            binary_audio += str(b & 1)
            pixel_count += 1
            # Emit progress update
            progress = int((pixel_count / total_pixels) * 100)
            socketio.emit('progress_update', {'progress': progress})  # Send progress to frontend
        # Remove the end marker
        binary_audio = binary_audio[:-16]
        audio_bytes = bytearray()
        for i in range(0, len(binary_audio), 8):
            byte = binary_audio[i:i+8]
            if len(byte) == 8:
                audio_bytes.append(int(byte, 2))
        with open(output_audio_path, 'wb') as audio_file:
            audio_file.write(audio_bytes)
        print(f"Extracted audio saved successfully at {output_audio_path}.")  # Debugging
        return True
    except Exception as e:
        print(f"Error extracting audio: {e}")  # Debugging
        flash(f"Error extracting audio: {e}")
        return False

def hide_video_in_image(cover_image_path, video_path, output_image_path):
    try:
        cover_image = Image.open(cover_image_path)
        video_bytes = get_video_bytes(video_path)
        binary_video = ''.join(format(byte, '08b') for byte in video_bytes) + '1111111111111110'  # Add end marker
        width, height = cover_image.size
        pixels = cover_image.load()
        binary_index = 0
        for y in range(height):
            for x in range(width):
                if binary_index < len(binary_video):
                    r, g, b = pixels[x, y]
                    r = (r & ~1) | int(binary_video[binary_index])
                    binary_index += 1
                    if binary_index < len(binary_video):
                        g = (g & ~1) | int(binary_video[binary_index])
                        binary_index += 1
                    if binary_index < len(binary_video):
                        b = (b & ~1) | int(binary_video[binary_index])
                        binary_index += 1
                    pixels[x, y] = (r, g, b)
                else:
                    break
        cover_image.save(output_image_path)
        print(f"Stego image saved successfully at {output_image_path}.")  # Debugging
        return True
    except Exception as e:
        print(f"Error hiding video: {e}")  # Debugging
        flash(f"Error hiding video: {e}")
        return False

def extract_video_from_image(stego_image_path, output_video_path):
    try:
        stego_image = Image.open(stego_image_path)
        binary_video = ""
        total_pixels = stego_image.width * stego_image.height
        pixel_count = 0
        for pixel in stego_image.getdata():
            r, g, b = pixel
            binary_video += str(r & 1)
            binary_video += str(g & 1)
            binary_video += str(b & 1)
            pixel_count += 1
            # Emit progress update
            progress = int((pixel_count / total_pixels) * 100)
            socketio.emit('progress_update', {'progress': progress})  # Send progress to frontend
        # Remove the end marker
        binary_video = binary_video[:-16]
        video_bytes = bytearray()
        for i in range(0, len(binary_video), 8):
            byte = binary_video[i:i+8]
            if len(byte) == 8:
                video_bytes.append(int(byte, 2))
        with open(output_video_path, 'wb') as video_file:
            video_file.write(video_bytes)
        print(f"Extracted video saved successfully at {output_video_path}.")  # Debugging
        return True
    except Exception as e:
        print(f"Error extracting video: {e}")  # Debugging
        flash(f"Error extracting video: {e}")
        return False

def get_unique_filename(base_path, filename):
    name, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(base_path, new_filename)):
        new_filename = f"{name}_{counter}{ext}"
        counter += 1
    return new_filename

def delete_expired_images(image_folder):
    for filename in os.listdir(image_folder):
        file_path = os.path.join(image_folder, filename)
        creation_time = os.path.getctime(file_path)
        if time.time() - creation_time > 24 * 3600:  # Delete files older than 24 hours
            os.remove(file_path)
# [Keep all your existing helper functions exactly as they were]
# ... (generate_otp, is_otp_valid, send_otp_email, text_to_bits, bits_to_text,
# get_image_bytes, get_audio_bytes, get_video_bytes, calculate_capacity,
# hide_data_in_image, extract_data_from_image, hide_image_in_image,
# extract_image_from_image, hide_audio_in_image, extract_audio_from_image,
# hide_video_in_image, extract_video_from_image, get_unique_filename,
# delete_expired_images)

# Debugging print to verify paths
print(f"Template folder: {app.template_folder}")
print(f"Upload folder: {UPLOAD_FOLDER}")
print(f"Extracted folder: {EXTRACTED_FOLDER}")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hide', methods=['GET', 'POST'])
def hide():
    if request.method == 'POST':
        # Check required fields
        if not all(key in request.form for key in ['email', 'data_type']) or \
           not all(key in request.files for key in ['cover_image', 'hidden_file']):
            flash("All fields are required.")
            return redirect(url_for('hide'))

        receiver_email = request.form['email']
        data_type = request.form['data_type']
        cover_image = request.files['cover_image']
        hidden_file = request.files['hidden_file']

        # Save cover image
        cover_image_filename = get_unique_filename(UPLOAD_FOLDER, 'cover_image.png')
        cover_image_path = os.path.join(UPLOAD_FOLDER, cover_image_filename)
        cover_image.save(cover_image_path)

        # Validate cover image size
        if os.path.getsize(cover_image_path) < COVER_IMAGE_MIN_SIZE:
            flash(f"Error: The cover image is too small. Minimum size is {COVER_IMAGE_MIN_SIZE / 1024:.2f} KB.")
            return redirect(url_for('hide'))

        # Calculate capacity
        capacity_kb = calculate_capacity(cover_image_path)

        # Validate hidden file size
        hidden_file.seek(0, os.SEEK_END)
        hidden_file_size_bytes = hidden_file.tell()
        hidden_file.seek(0)
        hidden_file_size_kb = hidden_file_size_bytes / 1024
        
        if hidden_file_size_kb > capacity_kb:
            flash(f"Error: The selected file size ({hidden_file_size_kb:.2f} KB) exceeds the maximum capacity ({capacity_kb:.2f} KB).")
            return redirect(url_for('hide'))

        # Save hidden file
        hidden_file_filename = get_unique_filename(UPLOAD_FOLDER, hidden_file.filename)
        hidden_file_path = os.path.join(UPLOAD_FOLDER, hidden_file_filename)
        hidden_file.save(hidden_file_path)

        # Generate output filename
        type_prefix = {
            'text': 'stego(txt)',
            'image': 'stego(img)',
            'audio': 'stego(audio)',
            'video': 'stego(video)'
        }.get(data_type, 'stego')
        
        output_image_filename = get_unique_filename(UPLOAD_FOLDER, f'{type_prefix}_image.png')
        output_image_path = os.path.join(UPLOAD_FOLDER, output_image_filename)

        # Hide the data
        hide_functions = {
            'text': hide_data_in_image,
            'image': hide_image_in_image,
            'audio': hide_audio_in_image,
            'video': hide_video_in_image
        }
        
        if not hide_functions[data_type](cover_image_path, hidden_file_path, output_image_path):
            return redirect(url_for('hide'))

        # Send email
        if not send_otp_email(receiver_email, output_image_path):
            return redirect(url_for('hide'))

        # Clean up
        delete_expired_images(UPLOAD_FOLDER)

        flash("Data hidden successfully! Check your email for the stego image and OTP.")
        return redirect(url_for('thank_you'))
    
    return render_template('hide.html')

@app.route('/extract', methods=['GET', 'POST'])
def extract():
    if request.method == 'POST':
        otp = request.form['otp']
        if is_otp_valid(otp):
            return redirect(url_for('extract_data_type'))
        flash('Invalid or expired OTP. Access denied.')
    return render_template('extract.html')

@app.route('/extract_data_type', methods=['GET', 'POST'])
def extract_data_type():
    if request.method == 'POST':
        if 'data_type' not in request.form or 'stego_image' not in request.files:
            flash("All fields are required.")
            return redirect(url_for('extract_data_type'))

        data_type = request.form['data_type']
        stego_image = request.files['stego_image']

        # Save stego image
        stego_image_filename = get_unique_filename(EXTRACTED_FOLDER, 'stego_image.png')
        stego_image_path = os.path.join(EXTRACTED_FOLDER, stego_image_filename)
        stego_image.save(stego_image_path)

        # Generate output filename
        output_file_filename = get_unique_filename(EXTRACTED_FOLDER, 
            f"extracted_{data_type}.{'txt' if data_type == 'text' else 'png' if data_type == 'image' else 'wav' if data_type == 'audio' else 'mp4'}")
        output_file_path = os.path.join(EXTRACTED_FOLDER, output_file_filename)

        # Extract data
        extract_functions = {
            'text': extract_data_from_image,
            'image': extract_image_from_image,
            'audio': extract_audio_from_image,
            'video': extract_video_from_image
        }
        
        if not extract_functions[data_type](stego_image_path, output_file_path):
            return redirect(url_for('extract_data_type'))

        flash("Data extracted successfully!")
        return redirect(url_for('success', file_path=output_file_path))
    
    return render_template('extract_data_type.html')

@app.route('/thank_you')
def thank_you():
    return render_template('thank_you.html')

@app.route('/success')
def success():
    file_path = request.args.get('file_path', '')
    return render_template('success.html', file_path=file_path)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(EXTRACTED_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
