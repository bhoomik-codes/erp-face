# 🧑‍💼 Vidhema ERP: Employee Face & Gesture Enabled Attendance System

A modern Django-based employee attendance system powered by **face recognition**, **gesture confirmation**, and an **AI Chat Assistant**. Designed for ease of use, automation, advanced reporting, and intelligent querying, this system streamlines employee attendance tracking with a premium interface.

## 🚀 Features

* **🔍 Face Recognition Attendance** 
  Mark attendance automatically using webcam-based face recognition directly from the browser.
* **🖐️ Hands-Free Gesture Confirmation** 
  The system securely confirms attendance with gestures (e.g., *Thumbs Up* to clock in, *Peace Sign* for break).
* **⏰ Automated Attendance Updates**  
  * **Lunch Out**: Automatically marks LUNCH_OUT if time exceeds typical limits.
  * **Daily Checkout**: Automatically marks OUT if no checkout by 11:00 PM.
* **👨‍💼 Admin Panel System & Employee Management**
  * Fully featured Admin dashboard to track employee hours, locations, and exceptions.
  * Add, edit, and delete employee data including facial reference images.
* **📊 Comprehensive Reporting**  
  * Filter attendance logs by **date range**, **employee**, **attendance type**, and **working hours**.  
* **📱 Responsive Design** 
  Works beautifully across desktops, tablets, and mobile devices with a state-of-the-art UI/UX.

## 🛠️ Setup and Installation

### 🔗 Prerequisites

* **Python 3.10+** (Tested with Python 3.14)
* **FFmpeg** Required for audio/speech processing.  
  * [Download FFmpeg](https://ffmpeg.org/download.html)
* **PostgreSQL / SQLite** (Defaults to SQLite for local development)
* **AWS S3** (Optional) For cloud-based photo storage. Falls back to local storage if keys are absent.

### 🐳 Easy Setup via Docker (Recommended)

To completely bypass complicated Python, OpenCV, and `dlib` compilation errors (especially common on Windows/macOS), you can run the entire system effortlessly using Docker.

1. **Install Docker:** Ensure you have [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
2. **Start the System:**
   ```bash
   docker-compose up --build
   ```
3. **Access the App:** Open your browser to `http://127.0.0.1:8000/attendance/`

*(Note: The Docker container automatically configures all dependencies, applies database migrations, and spins up the server. Any edits you make to the source code locally will instantly sync with the container!)*

### ⚙️ Manual Installation Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/bhoomik-codes/erp-face.git  
   cd erp-face
   ```

2. **Set up a Python virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: For Windows, a precompiled wheel for `dlib` is required for face recognition. Ensure you install the appropriate wheel for your Python version).*

4. **Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   # Database (Optional)
   # DB_NAME=...
   # DB_USER=...
   
   # AWS (Optional)
   # AWS_ACCESS_KEY_ID=...
   # AWS_SECRET_ACCESS_KEY=...
   # AWS_STORAGE_BUCKET_NAME=...
   # AWS_S3_REGION_NAME=...
   ```

5. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a Superuser (Admin)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the Development Server**
   ```bash
   python manage.py runserver
   ```

## 🧪 Usage Instructions

1. **Open the Web Interface**: Visit `http://127.0.0.1:8000/attendance/`
2. **Register Employees**: Log in as an admin, navigate to **Register Employee**, fill out the form, and capture a clear face photo.
3. **Mark Attendance**: Employees can go to **Mark Attendance**, stand in front of the webcam, and perform the requested gesture when recognized.
4. **View Reports**: Admins can view detailed attendance logs and export them via the **Dashboard**.

## 🧯 Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **dlib fails to install** | Ensure you have CMake and Visual Studio C++ Build Tools installed, or use a precompiled `.whl` file matching your Python version. |
| **Face encoding fails locally** | Ensure `MEDIA_ROOT` is writable. The system will fallback to local storage if AWS keys are not configured. |
| **Webcam not starting** | Ensure your browser has granted camera permissions to `localhost`. Browsers block webcam access on non-HTTPS domains unless it is `localhost`. |
| **Chatbot not responding** | Ensure PDFs are placed in `chatbot/documents/` and the FAISS index was successfully generated. |

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check [issues page](https://github.com/bhoomik-codes/erp-face/issues).

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is open source. Use it freely and contribute as you wish.
