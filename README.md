# Post Seal Vision System

A Python-based machine vision inspection application for seal quality monitoring and fail/pass decision logic using a live camera feed, ROI-based inspection, and optional Arduino servo actuation on failure detection.

## Overview

This project reads a camera stream, lets the user define inspection ROIs, analyzes the image in real time, and reports pass/fail results for:

- Upper sealing inspection
- Offset sealing inspection

When an inspection result is failing, the application can send a serial command to an Arduino Uno so that a servo performs a brief fail action and returns to its resting position.

## Features

- Live camera preview with grayscale and binary views
- ROI definition directly in the inspection view
- Real-time inspection based on binary threshold analysis
- Pass/fail summary in the main GUI
- Clear system log for inspection and Arduino activity
- Arduino serial communication helper for fail/pass signaling
- Support for simple servo fail-response behavior

## Project Structure

```text
FinalVersion/
├── arduino_serial.py         # Arduino serial helper class
├── camera.py                 # Camera capture and image processing
├── gui.py                    # Main PySide6 GUI application
├── inspection.py             # Inspection logic and summary generation
├── main.py                   # Application entry point
├── pyserial.py               # Simple serial test script for Arduino
├── requirements.txt          # Python dependencies
├── testConnectionArduino-Laptop.py
│                            # Quick serial connection test script
├── servo_fail_pulse/         # Arduino sketch folder
│   └── servo_fail_pulse.ino
├── __pycache__/              # Python cache directory
└── README.md                 # Project documentation
```

## Requirements

### Software

- Python 3.10 or newer
- OpenCV
- PySide6
- pyserial

### Hardware

- Laptop or desktop PC
- USB camera
- Arduino Uno
- Servo motor (e.g. MG996R)
- 5V servo power source recommended for reliable torque
- Wiring between Arduino and servo

## Installation

1. Open a terminal in the project folder:

```powershell
cd "c:\Firdaus\Projects\Post Seal Vision System\FinalVersion"
```

2. Create a virtual environment if desired:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyserial
```

## Run the app

From the project directory:

```powershell
cd "c:\Firdaus\Projects\Post Seal Vision System\FinalVersion"
python main.py
```

You can also optionally choose a camera index:

```powershell
python main.py --camera 0
```

## How to use the system

1. Connect the camera to the laptop.
2. Connect Arduino Uno to the laptop via USB.
3. Upload the Arduino sketch from `servo_fail_pulse/servo_fail_pulse.ino`.
4. Run the Python app.
5. Right-click the original camera image to open ROI-selection actions.
6. Select the inspection type and draw the ROI.
7. Define both required inspection ROIs:
   - `upper sealing`
   - `offset sealing`
8. Click `Start inspection`.
9. The app analyzes each frame and updates the pass/fail result.
10. When a fail condition is detected, the app sends a serial command to the Arduino.
11. The servo rotates briefly and returns to rest.

## Arduino behavior

The Arduino sketch expects commands such as:

- `FAIL`
- `PASS`
- `RESET`

The pulse sketch in `servo_fail_pulse/servo_fail_pulse.ino` performs this behavior:

- On `FAIL`: move to 90 degrees, hold briefly, then return to 0 degrees
- On `PASS` or `RESET`: return servo to rest position

## Wiring recommendation

For an MG996R servo:

- Servo signal pin -> Arduino digital pin 8
- Servo V+ -> 5V supply (recommended external 5V for reliable operation)
- Servo GND -> Arduino GND and external 5V ground common connection

> Important: Use a stable 5V power source for the servo if it is moving under load. Do not rely on the Arduino 5V pin alone for heavy servo motion.

## Troubleshooting

### Camera not opening

- Check the camera index with `--camera 0`, `--camera 1`, etc.
- Ensure the camera is plugged in and not already in use by another app.

### Serial port not working

- Close any Arduino Serial Monitor or other app using the COM port.
- Confirm the Arduino is connected and shows as a valid COM port.
- Install `pyserial` if the app says serial support is unavailable.

### Servo does not move

- Check that the sketch is uploaded to the Arduino.
- Check the signal wire is connected to the correct pin (D8 in the current sketch).
- Verify power and common ground wiring.
- Confirm you are using the pulse sketch rather than a non-moving test sketch.

### Inspection fails constantly

- Adjust the ROI positions.
- Check camera focus and lighting.
- Validate that the binary thresholding is suitable for your seal appearance.

## Notes

- The inspection logic is tuned for the current project conditions and uses binary white-ratio thresholds.
- The GUI intentionally keeps the system log visible for operator review.
- The Arduino helper is designed to fail gracefully when serial libraries are unavailable, so the app can still run without hardware attached.

## Quick test command for Arduino serial

If you want to verify the serial connection manually:

```powershell
cd "c:\Firdaus\Projects\Post Seal Vision System\FinalVersion"
python pyserial.py
```

## License

This project is a custom internal inspection application for the current vision system setup. Use and modify according to your project requirements.
