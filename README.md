# SMART-CAVE-MINING-SYSTEM
# VisionOS Pro v2: AIoT Smart Monitoring & Robotic System

## 📌 Project Overview
This project is an integrated **AIoT (Artificial Intelligence of Things)** ecosystem. It consists of a robotic car, an environmental monitoring station, and a central Command Center (HQ), all controlled via a sophisticated **PyQt6 GUI** with real-time **YOLOv8** computer vision integration.

## 🚀 Key Features
- **AI Vision Modules:** Dual-mode detection (PPE Safety Gear & Gemstone Analysis).
- **Environmental Monitoring:** Real-time tracking of Temperature, Humidity, Gas levels, Flood, and Seismic activity (Earthquake).
- **Robotic Control:** Smart car with obstacle avoidance, line tracking, and manual GUI override.
- **Unified Networking:** All nodes (Car, ENV, HQ) communicate via UDP protocol on a private network.

## 🛠 Tech Stack
- **Hardware:** ESP32 Microcontrollers, DHT22, MQ-Series Gas Sensors, Ultrasonic HC-SR04, L298N Motor Driver.
- **Firmware:** C++ (Arduino IDE).
- **Software:** Python 3.10+, OpenCV, PyQt6, Ultralytics (YOLOv8).

## 📁 File Structure
- `HQ_obstacle.ino`: The main network broker (Access Point).
- `fnal_envi__1_.ino`: Firmware for the environmental sensor node.
- `newest_car.ino`: Firmware for the robotic car with IR debounce logic.
- `main_gui_v_2.py`: The desktop application for monitoring and control.

## 🔧 Setup Instructions
1. **Hardware:** Flash the `.ino` files to their respective ESP32 boards.
2. **Python Environment:**
   ```bash
   pip install -r requirements.txt
