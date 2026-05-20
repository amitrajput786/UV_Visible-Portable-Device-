# AI-Integrated Portable Spectrofluorometer
### Quantitative Detection of Microplastic Contamination Using Carbon Dot Fluorescent Probes

**NIT Rourkela — Integrated M.Sc. Chemistry**  
**Amit Kumar** (Roll No: 421CY5075)  
Supervisor: Prof. Sasmita Mohapatra | Co-supervisor: Prof. Samit Ari  

---

## What This Project Does

A battery-powered, portable UV spectrofluorometer built from a Raspberry Pi 4B, Pi Camera Module 3, UV LEDs, and a hand-fabricated dark chamber. Carbon dot (CD)-loaded cellulose paper strips fluoresce blue-green under 365 nm UV; when polystyrene microplastics adsorb onto the strip, the fluorescence intensity shifts in a concentration-dependent way. A Python–Streamlit app running on the Pi extracts four fluorescence metrics from each camera image and uses linear regression calibration to predict concentration — no conventional spectrofluorometer needed.

**Best result:** 129.6 ppm predicted vs 130 ppm actual (0.3% error) for polystyrene in milk.

---

## Repository Structure

```
spectrofluorometer/
│
├── hardware/
│   └── spectrofluorometer.py     # Raspberry Pi control script
│                                 # (UV LEDs, camera, temperature sensor)
│
├── software/
│   └── app.py                    # Streamlit fluorescence analyser
│                                 # (ROI detection, calibration, prediction)
│
├── circuit/
│   ├── schematic.png             # KiCad circuit schematic
│   ├── bom.csv                   # Bill of Materials
│   └── pin_mapping.md            # J1 header → RPi GPIO mapping
│
├── docs/
│   └── Thesis.pdf                # Full thesis (CY-5994)
│
├── requirements.txt              # Python dependencies
└── README.md
```

---

## Hardware

| Component | Details |
|-----------|---------|
| Raspberry Pi 4B | Broadcom BCM2711, quad-core Cortex-A72, 4 GB RAM |
| Pi Camera Module 3 | Sony IMX708, 4608×2592, 12-bit, CSI interface |
| UV LEDs (D2, D4) | VAOL-5EUV0T4, 365/395 nm, 5mm, 20 mA |
| MOSFET (Q1) | IRLZ44N N-channel, logic-level gate |
| Temperature sensor (U1) | DS18B20, 1-Wire, GPIO4 |
| Current-limiting resistors | R3, R4 = 470 Ω (≈15 mA per LED at 9 V) |
| Gate resistor | R1 = 1 kΩ |
| Pull-up resistor | R2 = 4.7 kΩ (DS18B20 data line) |
| Decoupling capacitors | C1, C2 = 100 nF |
| Power — UV LEDs | 9 V battery via J2 screw terminal |
| Power — Raspberry Pi | 45 W USB-C adapter |

### GPIO Pin Mapping (J1 header)

| J1 Pin | Label | RPi Physical Pin | GPIO | Function |
|--------|-------|-----------------|------|----------|
| 1 | GPIO17 | 11 | GPIO 17 | UV LED control |
| 3 | GPIO4  | 7  | GPIO 4  | Temperature sensor data |
| 4 | +3.3V  | 1  | +3.3V   | Sensor VDD |
| 6 | GND    | 6  | GND     | Common ground |

---

## Software

### Hardware script — `hardware/spectrofluorometer.py`

Runs on the Pi. Controls the full measurement pipeline:
1. Reads DS18B20 temperature (safety check, ≤40 °C)
2. Turns UV LEDs ON via GPIO17 → IRLZ44N MOSFET
3. Waits 30 s for carbon dot fluorescence to stabilise
4. Captures auto-numbered JPEG + DNG RAW (Pi Camera Module 3)
5. Turns UV LEDs OFF, cleans up GPIO

```bash
python3 spectrofluorometer.py
# Saves: ~/project/images/fluorescence_XXXX.jpg
#        ~/project/images/fluorescence_XXXX.dng
```

Camera parameters locked at:
- ExposureTime = 35 000 µs
- AnalogueGain = 1.0
- AeEnable = False

### Analysis app — `software/app.py`

Streamlit web app. Runs on Pi or any PC on the same network.

```bash
streamlit run app.py
# Opens in browser at http://localhost:8501
```

**Tab 1 — Calibration:**
- Upload known-concentration images
- Type concentration (ppm) next to each image thumbnail
- Auto-detects fluorescent strip ROI (green-channel thresholding + scipy connected components)
- Computes G_mean, G/G₀, ΔG/G₀, G/B for every image
- Fits OLS linear regression for both G/B and G/G₀ models
- Shows calibration curves with R² and p-value

**Tab 2 — Predict Unknown:**
- Upload one unknown image
- App extracts metrics, applies saved calibration, back-calculates concentration
- Plots unknown as a star on the calibration curve with drop lines
- Shows full step-by-step algebra

**Tab 3 — Data & Export:**
- Full results table + residuals
- Download calibration CSV + equations summary CSV

### Fluorescence Metrics

| Metric | Formula | Notes |
|--------|---------|-------|
| G_mean | mean(green pixels in ROI) | Raw green channel intensity |
| G/G₀   | G_mean / G₀ | Normalised; G₀ = 135.0 (blank reference) |
| ΔG/G₀  | (G₀ − G_mean) / G₀ | Fractional quenching |
| G/B    | Σ(green pixels) / Σ(blue pixels) | Ratiometric; exposure-independent |

---

## Key Results

| Matrix | Metric | Equation | R² | p-value |
|--------|--------|----------|----|---------|
| Tap water | G/G₀ | G/G₀ = 0.001121×C + 1.1224 | 0.844 | 0.0035 |
| Tap water | G/B  | G/B = 0.000233×C + 0.8605 | 0.693 | 0.020  |
| Milk      | G/B  | G/B = 0.001636×C + 0.4668 | 0.911 | 0.012  |

Blind prediction (milk, unknown PS): **129.6 ppm** vs actual **130 ppm** → error **0.3%**

---

## Installation

### On Raspberry Pi

```bash
# Enable 1-Wire (for DS18B20)
sudo raspi-config  # Interface Options → 1-Wire → Enable

# Install dependencies
pip install streamlit numpy opencv-python-headless Pillow pandas scipy matplotlib --break-system-packages
pip install RPi.GPIO --break-system-packages
# picamera2 is pre-installed on Raspberry Pi OS Bullseye+

# Run hardware script
cd hardware/
python3 spectrofluorometer.py

# Run analysis app
cd software/
streamlit run app.py
```

### On PC (analysis only)

```bash
pip install -r requirements.txt
cd software/
streamlit run app.py
```

---

## Deep Learning (Future)

Architecture: MobileNetV2 backbone + Context Attention Block (CAB) + Multi-Scale Feature Fusion Block (MSFFB)  
Parameters: ~0.9 M  
Trained on: TensorFlow 2.19, NVIDIA RTX 3050  
Validated on: PBC (white blood cell), Brain Tumour, Skin Cancer datasets → 98.2% validation accuracy  
Next step: Train on fluorescence image dataset, convert to TFLite, deploy on Pi

---

## References

1. Stern & Volmer, *Physik. Z.* 1919, 20, 183
2. Han et al., *Molecules* 2024, DOI: 10.3390/molecules29071658
3. Permpool et al., *Microchemical Journal* 2025
4. Li et al., *Biosensors* 2022, DOI: 10.3390/bios12080668
5. Liu et al., *ACS Central Science* 2020, DOI: 10.1021/acscentsci.0c01306
6. Chen et al., *Environ. Sci. Technol. Lett.* 2021, DOI: 10.1021/acs.estlett.1c00483
7. Wang et al., *Sens. Actuators B* 2022, DOI: 10.1016/j.snb.2022.132347

---

## License

MIT License — free to use, modify, and distribute with attribution.
