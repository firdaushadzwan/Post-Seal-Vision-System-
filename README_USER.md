# Post Seal Vision System

## Quick start

This software checks seal quality using the live camera and shows PASS/FAIL results.

## Run the app

### Option 1: Run the EXE

Double-click this file:

- [FinalVersion/dist/PostSealVisionSystem.exe](dist/PostSealVisionSystem.exe)

### Option 2: Run from Python

Open PowerShell in the project folder and run:

```powershell
cd "c:\Firdaus\Projects\Post Seal Vision System\FinalVersion"
python main.py
```

## Setup

1. Connect the camera to the laptop.
2. Connect the Arduino Uno to the laptop.
3. Upload the Arduino sketch from:
   - [FinalVersion/servo_fail_pulse/servo_fail_pulse.ino](servo_fail_pulse/servo_fail_pulse.ino)
4. Make sure the servo is powered correctly.
5. Use a common ground between Arduino and servo power.

## How to use

1. Start the program.
2. Right-click the camera image.
3. Select the inspection type to define ROI.
4. Draw the ROI for:
   - `upper sealing`
   - `offset sealing`
5. Click Start inspection.
6. The system will display PASS/FAIL.
7. If the result is FAIL, the Arduino can trigger the servo pulse.

## Important notes

- Close Arduino IDE Serial Monitor before running the app, because it can block the COM port.
- The servo uses pin D8 in the Arduino code.
- Use an external 5V supply for the servo if it is heavy-duty.

## Troubleshooting

### Camera not detected

- Try different camera index values such as 0, 1, or 2.

### Arduino not responding

- Close any open Serial Monitor window.
- Check the correct COM port.
- Check the servo wiring and power.

### App does not start

- Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
python -m pip install pyserial
```

## Support

For technical help, review the main documentation here:

- [FinalVersion/README.md](README.md)
