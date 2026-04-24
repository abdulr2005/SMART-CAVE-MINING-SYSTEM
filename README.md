
# 🛰️ VisionOS Pro v2: AIoT Intelligence & Industrial Monitoring System

## 📝 Project Overview
**VisionOS Pro v2** is a high-performance **AIoT (Artificial Intelligence of Things)** ecosystem designed for industrial safety and automated environment monitoring. The system integrates real-time computer vision (YOLOv8) with a distributed sensor network (ESP32) and a mobile robotic unit, all orchestrated through a centralized **HQ Node** and a **PyQt6 Professional Dashboard**.

---

## 🏛️ System Architecture & Workflow
The system operates on a "Hub-and-Spoke" network topology where all nodes connect via a private WiFi network (**HQ_Network**) using the **UDP Protocol** on Port `4210`.

### 🖥️ 1. Central Command: Professional GUI (Lead Software)
The GUI is the brain of the system, handling high-level logic and data processing:
* **Dual-Core AI Inference**: Performs real-time YOLOv8 detection for PPE compliance and Gemstone analysis.
* **Live Telemetry**: Visualizes environmental data (Temp, Humidity, Gas) using interactive sparklines.
* **Control Interface**: Features a full D-Pad for manual car override and custom command transmission.
* **Alert Engine**: Processes danger states (QUAKE, GAS, HEAT) and logs them into a dedicated alert history.

### 📡 2. Networking Hub: HQ Node (ESP32)
* **Role**: Acts as the central Access Point and UDP message broker.
***Safety Logic**: Automatically activates physical actuators (Relays for fans, Buzzers for alarms) when danger signals are received from the environment node.

### 🌡️ 3. Sensory Unit: ENV Node (ESP32)
* **Role**: Monitors critical environmental factors and determines the system's "Safety State" based on a priority queue.
* **Priority Logic**: QUAKE (Highest) > ALL > GAS > HEAT > FLOOD > SAFE.

### 🏎️ 4. Robotic Unit: Car Node (ESP32)
* **Autonomous Safety**: Uses an Ultrasonic sensor to detect obstacles and trigger an emergency stop.
* **Precision Movement**: Implements IR sensor debounce logic to maintain stability during line tracking.

---

## 👥 Meet The Team
This project was a collaborative effort by students at **Misr University for Science and Technology (MUST)**, led by **Abdelrahman Elissawi**.

### 👑 Project Leader & Lead Software Engineer
**[Abdelrahman Elissawi](https://github.com/YourUsername)**
> *Focus: AI Architecture, Software Development & Systems Integration*
* **AI Development**: Trained and deployed the YOLOv8 models for PPE and Gemstone modules.
* **GUI Engineering**: Designed and programmed the entire PyQt6 Dashboard, including telemetry visualization and UDP networking.


### 👑 Project Leader & Hardware & IoT Collaborators
**[Eman Elsawy (Emmy)](https://github.com/Emmy-Elsawy)**
> *Focus: Hardware Implementation & IoT Support*
* **Hardware Design**: Led the implementation and assembly of the system's hardware components (ESP32 nodes, Sensors, and Car chassis).
* **Firmware Support**: Contributed to the development of the
* **Environment Node** firmware and sensor calibration.
* * **System Orchestration**: Defined the UDP communication protocol across all nodes.

---

## 🔧 Installation & Usage
1.  **Flash Firmware**: Upload the `.ino` files to their respective ESP32 boards (HQ, ENV, and Car).
2.  **Environment Setup**:
    ```bash
    pip install ultralytics opencv-python PyQt6 numpy
    ```
3.  **Run**: Execute `python main_gui_v_2.py` and ensure your PC is connected to the `HQ_Network`.

---
