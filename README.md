# ⛏️ SMART CAVE Mining System — AIoT Industrial Safety Platform

An integrated **AI + IoT + robotics** system designed for smart mining environments. The project combines real-time computer vision, distributed ESP32 sensor nodes, robotic control, UDP networking, and a PyQt6 monitoring dashboard.

## 🎯 Project Goal
Create a prototype industrial monitoring system capable of observing environmental conditions, detecting safety events, supporting computer-vision analysis, and coordinating hardware nodes from a centralized command interface.

## 🧩 System Architecture
The system follows a hub-and-spoke architecture over a private Wi-Fi network using UDP communication.

### 🖥️ Central Monitoring Dashboard
Built with **Python + PyQt6** to provide:
- Live environmental telemetry
- Alert history and danger-state monitoring
- Computer-vision inference
- Manual robotic control
- Command transmission between system nodes

### 👁️ Computer Vision
The AI layer uses **YOLOv8** for real-time visual detection tasks, including PPE-related detection and gemstone analysis.

### 📡 HQ Node — ESP32
Acts as the central networking hub and coordinates messages between distributed nodes. It can also trigger connected actuators such as alarms and relays in response to safety events.

### 🌡️ Environment Node — ESP32
Monitors environmental conditions such as temperature, humidity, gas, and other safety states.

### 🤖 Robotic Unit
A mobile ESP32-based unit supports obstacle detection, emergency stopping, line tracking, and manual control from the central dashboard.

## 🛠️ Tech Stack
**Python · YOLOv8 · OpenCV · PyQt6 · ESP32 · Arduino/C++ · UDP Networking · Computer Vision · IoT · Robotics**

## 📂 Repository Structure
- `AI_models/` — AI-related assets and models
- `CAR_CODE/` — robotic unit firmware/code
- `ENVI_CODE/` — environmental monitoring node
- `HQ_CODE/` — central networking node
- `project_gui/` — desktop monitoring interface

## 🚀 Setup
Install the Python dependencies:

```bash
pip install ultralytics opencv-python PyQt6 numpy
```

Flash the corresponding firmware to the ESP32 nodes, connect the computer to the system network, and run the GUI from the project interface code.

## 👥 Team
Developed as a collaborative student project at **Misr University for Science and Technology (MUST)**.

**Abdulrahman Elissawi** — Project Lead / AI & Software  
Focus: AI architecture, YOLOv8 integration, GUI development, networking, and system integration.

**Eman Elsawy (Emmy)** — Hardware & IoT  
Focus: hardware implementation, ESP32 nodes, sensors, firmware support, and system integration.

---
**Portfolio focus:** AIoT · Computer Vision · Embedded Systems · Robotics · Industrial Safety
