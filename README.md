# **🧑‍💼 Employee Face & Gesture Enabled Attendance System with AI Chatbot**

A Django-based employee attendance system powered by **face recognition**, **gesture confirmation**, and an **AI Chat Assistant**. Designed for ease of use, automation, advanced reporting, and intelligent querying, this system streamlines employee attendance tracking with a modern touch.

## **🚀 Features**

* **🔍 Face Recognition Attendance** Mark attendance automatically using webcam-based face recognition.  
* **🖐️ Hands-Free Gesture Confirmation** System asks: *"Please make a Thumbs Up gesture to mark your Attendance"*  
  Marks attendance based on your shown gesture.  
* **⏰ Automated Attendance Updates**  
  * **Lunch Out**: Automatically set LUNCH\_OUT if LUNCH\_IN and time \> 2:30 PM.  
  * **Daily Checkout**: Automatically set OUT if no checkout by 11:00 PM.  
* **🤖 AI Chat Assistant** An integrated chatbot on the admin dashboard for quick queries regarding attendance records, leave information, and general system information based on provided documentation (PDFs).  
* **Admin Panel System**  
* **👨‍💼 Employee Management** \- Edit existing employee data using the admin panel accessed at http://127.0.0.1:8000/attendance/admin\_login.  
  * Add new employees with personal details and a photo for face recognition at the admin panel.  
* **📊 Attendance Report & Filtering**  
  * Filter by **date range**, **employee**, **attendance type**, and **working hours**.  
* **📱 Responsive Design** Works across desktops, tablets, and mobile devices.

## **🛠️ Setup and Installation (Windows)**

### **🔗 Prerequisites**

* **Python 3.x** [Download Python](https://www.python.org/downloads/) and add it to your PATH.  
* **FFmpeg** Required for audio processing.  
  [Download FFmpeg](https://ffmpeg.org/download.html)  
  [How to Install FFmpeg on Windows](https://www.geeksforgeeks.org/how-to-install-ffmpeg-on-windows/)  
* **dlib Precompiled Wheel** Save dlib-19.24.99-cp313-cp313-win\_amd64.whl inside ./wheels/ in your root directory.  
* Chatbot Knowledge Base (PDFs)  
  Place any PDF documents you want the chatbot to learn from into the chatbot/documents/ directory. These will be used to build the knowledge base for answering queries.

### **⚙️ Installation Steps**

git clone \<your-repository-url\>  
cd \<your-project-directory\>  
run\_server.bat

This script will:

* Set up a Python virtual environment  
* Install the dlib wheel and other dependencies (including transformers, sentence-transformers, faiss-cpu, PyMuPDF)  
* Check for FFmpeg  
* Apply migrations  
* **Build the Chatbot's FAISS index and embeddings from PDFs in chatbot/documents/ (this might take some time on the first run).**  
* Launch the Django development server

## **🧪 Usage Instructions**

### **🔹 1\. Open the Web Interface**

Visit: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### **🔹 2\. Register Employees**

Navigate to **Register Employee**, fill the form, and upload a clear face photo.

### **🔹 3\. Mark Attendance**

* Go to **Mark Attendance** \- Stand in front of webcam  
* System asks: *"Do you want to mark your attendance?"*  
* Say **"yes"** or **"no"**

### **🔹 4\. View Attendance Reports**

Go to **View Attendance Report** Apply filters:

* 📅 Date Range  
* 🧑 Specific Employees  
* 📍 Attendance Types  
* ⏱️ Worked Hours Less Than X

### **🔹 5\. Use the AI Chat Assistant (Admin Dashboard)**

* Navigate to the **Admin Dashboard**.  
* Click the floating chatbot icon (💬) in the bottom right corner to open the chat window.  
* Type your questions, such as:  
  * "What is employee 123's attendance for this month?"  
  * "How many leaves does employee John Doe have?"  
  * "What is the policy for overtime?" (if this is in your PDFs)  
* The chatbot will try to answer based on the loaded documents and employee data.

## **🗂️ Project Structure (Simplified)**

your-project/  
│  
├── manage.py  
├── requirements.txt  
├── run\_server.bat  
├── wheels/  
│   └── dlib-19.24.99-cp313-cp313-win\_amd64.whl  
│  
├── attendance\_app/  
│   ├── management/  
│   ├── migrations/  
│   ├── services/  
│   ├── static/  
│   │   ├── css/  
│   │   ├── img/  
│   │   ├── js/  
│   │   │   ├── admin\_scripts.js         \# Admin dashboard specific JS, including chatbot UI logic  
│   │   │   ├── employee\_management.js   \# Employee management specific JS  
│   │   │   └── common\_utils.js          \# Reusable JS functions (e.g., displayMessage, delete modal)
│   │   └── models/                       \# Model files for gesture recognitions   
│   ├── templates/  
│   ├── views.py  
│   ├── models.py  
│   └── urls.py  
│  
├── chatbot/  
│   ├── documents/                     \# Place PDFs for chatbot knowledge base here  
│   ├── embeddings/                    \# Stores generated text embeddings (texts.pkl)  
│   ├── faiss\_index/                   \# Stores the FAISS index (index.faiss)  
│   ├── migrations/  
│   ├── static/  
│   ├── templates/  
│   ├── \_\_pycache\_\_/  
│   ├── chatbot\_core.py                \# Main chatbot logic, LLM interaction, RAG  
│   ├── generate\_embeddings.py         \# Script to process PDFs and create embeddings/index  
│   ├── urls.py  
│   └── views.py  
│  
├── media/                             \# Stores uploaded employee photos etc.  
├── vidAttendence2/                    \# Your main Django project config  
└── wheels/                            \# Precompiled Python packages

## **🧯 Troubleshooting**

| Issue                                         | Solution |
|:----------------------------------------------| :---- |
| **Python not found**                          | Ensure Python is installed and added to PATH |
| **FFmpeg errors**                             | Verify installation and ffmpeg/bin is in PATH |
| **dlib fails to install**                     | Ensure .whl file matches Python version and is in ./wheels/ |
| **Voice not detected**                        | Allow microphone permissions in browser |
| **Speech not recognized**                     | Ensure clear audio; check internet if using online recognition |
| **Wrong attendance marking**                  | Debug logic in views.py → determine\_attendance\_type() |
| **Chatbot not responding / Empty responses**  | Check Django server console for DEBUG print statements from chatbot\_core.py. Ensure PDFs are in chatbot/documents/ and the FAISS index was successfully created. Look for "DEBUG: Final response from generate\_response: ''" (empty string) to indicate the model returned nothing. |
| **Chatbot UI not appearing/functional**       | Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R). Ensure admin\_scripts.js and common\_utils.js are loaded as type="module" in admin\_dashboard.html. Check browser console for JavaScript errors related to element IDs. |
| **"Employee not found" from chatbot**         | Verify the user\_id being passed from the frontend (Django's request.user.id) corresponds to an existing Employee record's primary key (id) or employee\_id field. Adjust logic in chatbot\_core.py (get\_attendance\_summary, get\_leave\_info) to match how your Employee records are identified. |

---

## 🤝 Contributing

Feel free to:
- Fork the repo
- Submit pull requests
- Report bugs or request features

---

## 📜 License

This project is open source. Use it freely and contribute as you wish.

---