# Windows 11 Beginner Setup Guide

This guide walks you step-by-step through setting up and running the AGRI Smart Irrigation project on Windows 11 using PowerShell.

---

## Prerequisites Check

Open Windows PowerShell in the project directory:
```powershell
cd "c:\Users\DELL\OneDrive\Desktop\Major Project\AGRI_PROJECT"
```

Verify your Python installation:
```powershell
python --version
```
*(Your system has Python 3.14.3 installed).*

---

## Step 1: Create a Python Virtual Environment

A virtual environment ensures project packages don't interfere with system Python:

```powershell
python -m venv venv
```

Activate the virtual environment:
```powershell
.\venv\Scripts\Activate.ps1
```

> **Note on PowerShell Execution Policy**:
> If PowerShell gives an error saying `script execution is disabled on this system`, run this once:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```
> Then retry `.\venv\Scripts\Activate.ps1`.

---

## Step 2: Install Dependencies

With the virtual environment activated, install the backend and simulator requirements:

```powershell
python -m pip install -r backend/requirements.txt
python -m pip install -r simulator/requirements.txt
```

---

## Step 3: Run the Backend Application

In your first PowerShell window:
```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Once started, open your web browser to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

You will see the AGRI Smart Irrigation Dashboard live! Interactive API docs are also available at `http://127.0.0.1:8000/docs`.

---

## Step 4: Run the Sensor Simulator

Open a **second** PowerShell window, navigate to the project directory, activate the environment, and run the simulator:

```powershell
cd "c:\Users\DELL\OneDrive\Desktop\Major Project\AGRI_PROJECT"
.\venv\Scripts\Activate.ps1
python simulator/sensor_simulator.py
```

You will see live simulated temperature, humidity, and soil moisture data streaming into the terminal and appearing in real-time on your browser dashboard!
