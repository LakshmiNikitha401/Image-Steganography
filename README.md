# 🔐 Image Steganography with OTP Security
**A high-security, multi-format data concealment system using LSB embedding and automated SMTP verification.**

---

## 📌 Project Overview
* **End-to-End Security:** A web-based application designed to obscure both the data and the existence of communication.
* **Core Technique:** Utilizes Least Significant Bit (LSB) to hide data in the noise of image pixels.
* **Innovation:** Integrates a One-Time Password (OTP) layer to prevent unauthorized extraction.
* **Scope:** Analyzed for performance, capacity, and imperceptibility to ensure 100% extraction accuracy.

---

## 🛠 Tools & Technologies
* **Python (Flask):** Server-side logic, routing, and session management.
* **OpenCV / Pillow:** Advanced image processing for pixel-level LSB manipulation.
* **SMTP (smtplib):** Automated email delivery system for secure OTP transmission.
* **Front-End:** HTML5/CSS3 and JavaScript for a responsive, user-friendly dashboard.

---

## 📁 Dataset & Capacity Handling
The system performs **Real-Time Capacity Validation** before any data is hidden to prevent image corruption.

* **Input Data:** Supports Text (.txt), Images (.jpg, .png), Audio (.mp3), and Video (.mp4).
* **Capacity Formula:** $C = W \times H \times 3 \times 1$ (Width × Height × RGB Channels × 1-bit LSB).
* **Validation:** Automatically halts the process if the secret file size exceeds the calculated capacity.

---

## 📊 Workflow & Logic


### **Hiding Process**
* **Encoding:** Converts secret data into binary and embeds it into the LSBs of the cover image.
* **Security:** Generates a 4-digit OTP and triggers an automated email to the recipient.

### **Extraction Process**
* **Authentication:** Requires the unique OTP received via email to unlock the "stego" image.
* **Reconstruction:** Rebuilds the original binary data into its native file format with zero data loss.

---

## 💡 Key Insights & Results
* **100% Extraction Accuracy:** Verified that extracted files are identical to original source files.
* **Visual Integrity:** Modifications remain completely imperceptible to the human eye under standard viewing conditions.
* **Scalability:** Successfully tested with high-resolution images ($3072 \times 4096$) handling up to 4.6MB of hidden data.

---

## 🏆 Awards & Publications
* **3rd Prize Winner:** HITAM Project Expo 2025.
* **Research Paper:** Published in the **International Journal of Research and Analytical Reviews (IJRAR)**.

---

## 🖥️ Interface Preview
*(Upload your own screenshots here to match the friend's "Dashboard Preview" style)*

| Hiding Interface | Extraction & OTP Verification |
| :--- | :--- |
| ![Hiding UI](Screenshot 2026-05-16 184905.png") | ![Extraction UI]("C:\Users\laksh\OneDrive\Pictures\Screenshots 1\Screenshot 2026-05-16 184954.png") |
