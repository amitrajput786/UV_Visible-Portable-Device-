"""
spectrofluorometer.py
=====================
Main hardware control script for the AI-Integrated Portable Spectrofluorometer.
Runs on Raspberry Pi 4B (Raspberry Pi OS).

Hardware:
  - Pi Camera Module 3 (Sony IMX708) via CSI
  - UV LEDs 365/395 nm controlled via IRLZ44N MOSFET on GPIO17
  - DS18B20 1-Wire temperature sensor on GPIO4
  - Custom PCB (J1 header → RPi GPIO, J2 → 12V external PSU)

GPIO Pin Mapping (J1 header):
  J1 Pin 1  →  RPi Pin 11  (GPIO17) — UV LED MOSFET gate
  J1 Pin 3  →  RPi Pin 7   (GPIO4)  — DS18B20 data (1-Wire)
  J1 Pin 4  →  RPi Pin 1   (+3.3V)  — Sensor VDD
  J1 Pin 6  →  RPi Pin 6   (GND)    — Common ground

Usage:
  python3 spectrofluorometer.py

Images are saved as:
  ~/project/images/fluorescence_XXXX.jpg   (JPEG)
  ~/project/images/fluorescence_XXXX.dng   (RAW DNG)

Author: Amit Kumar (421CY5075), NIT Rourkela
"""

import RPi.GPIO as GPIO
import time
import os
import glob
from picamera2 import Picamera2
from libcamera import controls

# ── Configuration ─────────────────────────────────────────────────────────────
UV_LED_PIN    = 17                          # GPIO17 → MOSFET gate → UV LEDs
SENSOR_BASE   = '/sys/bus/w1/devices/'      # 1-Wire sysfs path
EXPOSURE_TIME = 35000                       # Camera exposure in microseconds (locked)
ANALOGUE_GAIN = 1.0                         # Camera gain (locked)
UV_WARMUP_SEC = 30                          # UV excitation time before capture
MAX_TEMP_C    = 40.0                        # Safety cutoff — LEDs off if exceeded
IMAGE_DIR     = os.path.expanduser('~/project/images')

os.makedirs(IMAGE_DIR, exist_ok=True)

# ── GPIO Setup ────────────────────────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setup(UV_LED_PIN, GPIO.OUT)
GPIO.output(UV_LED_PIN, GPIO.LOW)           # LEDs OFF at startup

# ── Temperature Sensor ────────────────────────────────────────────────────────
def read_temperature():
    """Read DS18B20 via 1-Wire sysfs interface. Returns float °C or None."""
    try:
        devices = glob.glob(SENSOR_BASE + '28*')
        if not devices:
            print("WARNING: DS18B20 not found. Check Pin 1=3.3V, Pin 2=Data, Pin 3=GND.")
            return None
        sensor_file = devices[0] + '/w1_slave'
        with open(sensor_file, 'r') as f:
            lines = f.readlines()
        # Wait for valid CRC
        retries = 0
        while lines[0].strip()[-3:] != 'YES' and retries < 5:
            time.sleep(0.2)
            with open(sensor_file, 'r') as f:
                lines = f.readlines()
            retries += 1
        idx = lines[1].find('t=')
        if idx != -1:
            return round(float(lines[1][idx + 2:]) / 1000.0, 2)
    except Exception as e:
        print(f"Temperature read error: {e}")
    return None

# ── UV LED Control ─────────────────────────────────────────────────────────────
def uv_led_on():
    GPIO.output(UV_LED_PIN, GPIO.HIGH)
    print("UV LEDs ON")

def uv_led_off():
    GPIO.output(UV_LED_PIN, GPIO.LOW)
    print("UV LEDs OFF")

# ── Auto-numbered filename ─────────────────────────────────────────────────────
def get_next_index(folder):
    """Find next available 4-digit index so images are never overwritten."""
    existing = glob.glob(os.path.join(folder, 'fluorescence_*.jpg'))
    if not existing:
        return 1
    indices = []
    for f in existing:
        base = os.path.basename(f)
        try:
            indices.append(int(base.split('_')[1].split('.')[0]))
        except (IndexError, ValueError):
            pass
    return max(indices) + 1 if indices else 1

# ── Camera Capture ─────────────────────────────────────────────────────────────
def capture_image(idx):
    """
    Capture JPEG + DNG RAW with locked exposure and gain.
    Autofocus is run once before locking all parameters.
    Returns (jpeg_path, dng_path).
    """
    jpeg_path = os.path.join(IMAGE_DIR, f'fluorescence_{idx:04d}.jpg')
    dng_path  = os.path.join(IMAGE_DIR, f'fluorescence_{idx:04d}.dng')

    picam2 = Picamera2()

    # Still config: full resolution main stream + raw stream for DNG
    config = picam2.create_still_configuration(
        main={"size": (4608, 2592)},
        raw={"size": picam2.sensor_resolution},
    )
    picam2.configure(config)

    print("Starting camera...")
    picam2.start()
    time.sleep(3)  # Allow sensor to settle

    # Run autofocus once, then lock
    print("Running autofocus...")
    picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfTrigger": 0})
    time.sleep(2)

    # Lock all camera parameters for reproducible measurements
    picam2.set_controls({
        "AeEnable":     False,
        "ExposureTime": EXPOSURE_TIME,
        "AnalogueGain": ANALOGUE_GAIN,
        "AfMode":       controls.AfModeEnum.Manual,
    })
    time.sleep(1)

    print(f"Capturing image {idx:04d}...")
    request = picam2.capture_request()

    # Save JPEG
    request.save("main", jpeg_path)

    # Save DNG RAW (try multiple API signatures for picamera2 version compatibility)
    try:
        request.save_dng(dng_path)
    except TypeError:
        try:
            raw_array = request.make_array("raw")
            metadata  = request.get_metadata()
            picam2.helpers.save_dng(raw_array, metadata,
                                    picam2.camera_configuration()["raw"],
                                    dng_path)
        except Exception as e:
            print(f"DNG save skipped ({e}). JPEG is sufficient for analysis.")

    request.release()
    picam2.stop()
    picam2.close()

    print(f"  JPEG : {jpeg_path}")
    print(f"  RAW  : {dng_path}")
    return jpeg_path, dng_path

# ── Main Measurement Pipeline ─────────────────────────────────────────────────
def run_measurement():
    print("=" * 55)
    print("  AI-Integrated Portable Spectrofluorometer")
    print("  NIT Rourkela — Amit Kumar (421CY5075)")
    print("=" * 55)

    # Step 1: Temperature check
    temp = read_temperature()
    if temp is not None:
        print(f"Temperature: {temp:.2f} °C")
        if temp > MAX_TEMP_C:
            print(f"ERROR: Temperature {temp}°C exceeds limit ({MAX_TEMP_C}°C). Aborting.")
            return
    else:
        print("WARNING: Temperature sensor unavailable. Proceeding with caution.")

    # Step 2: Get next image number
    idx = get_next_index(IMAGE_DIR)
    print(f"Next image index: {idx:04d}")

    # Step 3: UV LEDs ON — excite carbon dot fluorescence
    uv_led_on()
    print(f"Waiting {UV_WARMUP_SEC}s for fluorescence excitation...")
    time.sleep(UV_WARMUP_SEC)

    # Step 4: Capture image
    jpeg_path, dng_path = capture_image(idx)

    # Step 5: UV LEDs OFF
    uv_led_off()

    print("=" * 55)
    print("Measurement complete.")
    print(f"Analyse image using:  streamlit run app.py")
    print("=" * 55)

# ── Entry Point ───────────────────────────────────────────────────────────────
try:
    run_measurement()
finally:
    # Ensure LEDs are always turned off even on crash
    GPIO.output(UV_LED_PIN, GPIO.LOW)
    time.sleep(0.3)
    GPIO.cleanup()
    print("GPIO cleaned up. Safe to disconnect.")
