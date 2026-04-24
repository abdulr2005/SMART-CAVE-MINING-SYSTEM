
# 🛰️ VisionOS Pro v2: AIoT Intelligence & Industrial Monitoring System

## 📝 Project Overview
**VisionOS Pro v2** is a high-performance **AIoT (Artificial Intelligence of Things)** ecosystem designed for industrial safety and automated environment monitoring. [cite_start]The system integrates real-time computer vision (YOLOv8) with a distributed sensor network (ESP32) and a mobile robotic unit, all orchestrated through a centralized **HQ Node** and a **PyQt6 Professional Dashboard**[cite: 1, 102].

---

## 🏛️ System Architecture & Workflow
[cite_start]The system operates on a "Hub-and-Spoke" network topology where all nodes connect via a private WiFi network (**HQ_Network**) using the **UDP Protocol** on Port `4210`[cite: 1, 2, 4, 104].

### 🖥️ 1. Central Command: Professional GUI (Lead Software)
[cite_start]The GUI is the brain of the system, handling high-level logic and data processing[cite: 1]:
* [cite_start]**Dual-Core AI Inference**: Performs real-time YOLOv8 detection for PPE compliance and Gemstone analysis[cite: 1].
* [cite_start]**Live Telemetry**: Visualizes environmental data (Temp, Humidity, Gas) using interactive sparklines[cite: 1].
* [cite_start]**Control Interface**: Features a full D-Pad for manual car override and custom command transmission[cite: 1].
* [cite_start]**Alert Engine**: Processes danger states (QUAKE, GAS, HEAT) and logs them into a dedicated alert history[cite: 1, 3, 25].

### 📡 2. Networking Hub: HQ Node (ESP32)
* [cite_start]**Role**: Acts as the central Access Point and UDP message broker[cite: 102, 142].
* [cite_start]**Safety Logic**: Automatically activates physical actuators (Relays for fans, Buzzers for alarms) when danger signals are received from the environment node[cite: 112, 116].

### 🌡️ 3. Sensory Unit: ENV Node (ESP32)
* [cite_start]**Role**: Monitors critical environmental factors and determines the system's "Safety State" based on a priority queue[cite: 1, 23].
* [cite_start]**Priority Logic**: QUAKE (Highest) > ALL > GAS > HEAT > FLOOD > SAFE[cite: 3, 18, 23].

### 🏎️ 4. Robotic Unit: Car Node (ESP32)
* [cite_start]**Autonomous Safety**: Uses an Ultrasonic sensor to detect obstacles and trigger an emergency stop[cite: 37, 89].
* [cite_start]**Precision Movement**: Implements IR sensor debounce logic to maintain stability during line tracking[cite: 27, 45].

---

## 👥 Meet The Team
This project was a collaborative effort by students at **Misr University for Science and Technology (MUST)**, led by **Abdelrahman Elissawi**.

### 👑 Project Leader & Lead Software Engineer
**[Abdelrahman Elissawi](https://github.com/YourUsername)**
> *Focus: AI Architecture, Software Development & Systems Integration*
* [cite_start]**AI Development**: Trained and deployed the YOLOv8 models for PPE and Gemstone modules[cite: 1].
* [cite_start]**GUI Engineering**: Designed and programmed the entire PyQt6 Dashboard, including telemetry visualization and UDP networking[cite: 1].
* [cite_start]**System Orchestration**: Defined the UDP communication protocol across all nodes[cite: 1, 101].

### 🛠️ Hardware & IoT Collaborators
**[Eman Elsawy (Emmy)](https://github.com/Emmy-Elsawy)**
> *Focus: Hardware Implementation & IoT Support*
* [cite_start]**Hardware Design**: Led the implementation and assembly of the system's hardware components (ESP32 nodes, Sensors, and Car chassis)[cite: 27, 30, 99].
* [cite_start]**Firmware Support**: Contributed to the development of the **Environment Node** firmware and sensor calibration[cite: 1].

---

## 🔧 Installation & Usage
1.  [cite_start]**Flash Firmware**: Upload the `.ino` files to their respective ESP32 boards (HQ, ENV, and Car)[cite: 1, 99].
2.  **Environment Setup**:
    ```bash
    pip install ultralytics opencv-python PyQt6 numpy
    ```
3.  [cite_start]**Run**: Execute `python main_gui_v_2.py` and ensure your PC is connected to the `HQ_Network`[cite: 1, 4].

---
