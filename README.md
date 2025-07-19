# 🔥 VerticalShelter Backend

This is the **official backend** of the VerticalShelter app — a FastAPI-based server using **Firebase**, **Uvicorn**, and **Google Cloud** services to support real-time climbing data and authentication.

It is still in construction. If you can`t make it works, contact the owner.

---

## 🚀 Tech Stack

- **FastAPI** – Modern web framework
- **Firebase** – Auth, Firestore, Cloud Storage
- **Uvicorn** – ASGI server
- **BigQuery** – Analytics & reporting
- **Pyrebase** – Firebase SDK wrapper
- **Google Cloud SDKs**

---

## 🔐 Firebase Setup (Required Before Running)

This is a ChatGPT setup instruction :

You **must create and configure a Firebase project** before running the backend.

### 1. Create a Firebase Project

- Go to [Firebase Console](https://console.firebase.google.com/)
- Click **“Add Project”** and follow the steps
- Enable:
  - **Firestore**
  - **Authentication (email/password)**
  - **Cloud Storage**

### 2. Get Firebase Config

Go to:
- **Project Settings > General > Your Apps > SDK Setup & Configuration**
- Select **Web App**
- Copy the config dictionary — you’ll need it in step 4.

### 3. Generate Admin SDK Credentials

- Go to **Settings > Service Accounts**
- Click **“Generate new private key”**
- Download the `.json` file
- Place it inside the repo at: XXXX.json, and replace XXX by a name then replace XXXX in settings.py


### 4. Add Firebase Configs (Python)

Create two files:

#### `app/configfiles/dev.py`

```python
firebaseConfig = {
    "apiKey": "YOUR_API_KEY",
    "authDomain": "your-app.firebaseapp.com",
    "projectId": "your-project-id",
    "storageBucket": "your-app.appspot.com",
    "messagingSenderId": "XXXXXXXXX",
    "appId": "1:XXXX:web:XXXX",
    "measurementId": "G-XXXXXXX"
}

BUCKET_NAME = "your-app.appspot.com"
```
## 🧪 Local Development

### 1. Clone the Repository

```bash
git clone https://github.com/Vertical-Shelter/VerticalShelter-Back.git
cd VerticalShelter-Back
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

You can either create a `.env` file or set manually:

```bash
export ENV_MODE=dev
export CLOUDRUN_SERVICE_URL=http://localhost:8000  # Optional
```
### 5. Run the Server

```bash
uvicorn app.main:app --reload
```
Your API is now running at `http://localhost:8000`

---

## 📫 Contact

Need help or want to contribute?  
Feel free to open an issue or contact the maintainer.

---

## 📄 License

This project is licensed under a **Custom License – Non-Commercial Use Only**.

You may:

- Use the code for personal or academic purposes
- Contribute via pull requests

You may **not**:

- Use the code in a commercial product or service without explicit permission
- Redistribute or resell the backend or derivatives

> 📬 For commercial licensing, please contact: **vertical.shelter.app@gmail.com**

See the full terms in the [`LICENSE`](./LICENSE) file.


