# MeetingTimer ⏱️

**MeetingTimer** is a **Flask-based** (Python) application designed for synchronized management and automation of timing during meetings. 

The system allows an administrator to control the timeline and duration of individual speeches in real time, distributing updates to all connected clients via a smooth **Server-Sent Events (SSE)** communication.

---

## ✨ Main Features

*   **Real-Time Synchronization**: Instant updates across all connected clients (control room screens, podium, displays) via SSE (Server-Sent Events).
*   **Proportional Compensation Algorithm**: If a speech exceeds the established time, the system automatically and proportionally recalculates the duration of future timers (longer than 5 minutes) to ensure the meeting's maximum limit (e.g., 105 nominal minutes) is respected.
*   **Template Management**: Pre-defined agenda loading based on the day of the week (`infrasettimanale_std` / `fine_settimana_std`) via JSON configuration files.
*   **Automated Scraping**: Integration for dynamic extraction of the program and speech titles at startup.
*   **Portable Architecture**: Prepared to run either as a Python script or as a "frozen" standalone executable (e.g., via PyInstaller), saving the application state in the `AppData` folder (Windows) or `Home` (Linux/macOS).
*   **Multi-Interface**: 
    *   `http://127.0.0.1:1914/admin` - Admin control panel.
    *   `http://127.0.0.1:1914/` - Client.

---

## 🛠️ Technology and Stack

*   **Backend**: Python, Flask, Multithreaded core (Queue/Timer).
*   **Frontend**: HTML5, CSS3, JavaScript (Vanilla ES6).
*   **Network Protocol**: Server-Sent Events (SSE) for low-latency, unidirectional data streaming.

---

## 🚀 Quick Start and Installation

### Procedure
1. Download executable file

[![](https://img.shields.io/badge/Download-MeetingTimer.exe-green?style=for-the-badge&logo=windows)](https://github.com/Gabriele-DM-unimol/MeetingTimer/releases/download/1.0.1/MeetingTimer-linux)

[![Download WINDOWS](https://img.shields.io/badge/Download-MeetingTimer.exe-green?style=for-the-badge&logo=windows)](https://github.com/Gabriele-DM-unimol/MeetingTimer/releases/download/1.0.1/MeetingTimer.exe)

[![Download MACOS](https://img.shields.io/badge/Download-MeetingTimer.exe-green?style=for-the-badge&logo=windows)](https://github.com/Gabriele-DM-unimol/MeetingTimer/releases/download/1.0.1/MeetingTimer-mac)

2. Run MeetingTimer

It is recommended to use Chromium-based browsers (Google Chrome, Edge etc.)