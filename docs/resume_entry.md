# Resume — Project Entry

## AI-Integrated Portable Spectrofluorometer
**NIT Rourkela | Jan 2025 – May 2026**
*Integrated M.Sc. Research Project (CY-5994)*

---

### One-Line Summary (for resume headline / profile)

> Built a battery-powered portable spectrofluorometer on Raspberry Pi 4B that detects polystyrene microplastics in food and water samples with 0.3% prediction error — no lab equipment needed.

---

### Resume Bullet Points (pick 4–5 depending on space)

- Designed and fabricated a **portable UV spectrofluorometer** integrating Raspberry Pi 4B, Pi Camera Module 3 (IMX708), 365 nm UV LEDs, IRLZ44N MOSFET driver circuit, and DS18B20 temperature sensor on a custom KiCad PCB inside a hand-built light-tight dark chamber.

- Synthesised **N-doped carbon dot (CD) fluorescent probes** via one-step hydrothermal process; immobilised CDs on cellulose paper strips for disposable, low-cost microplastic sensing.

- Developed a **Python–Streamlit RGB fluorescence analyser** with automatic ROI detection (green-channel thresholding + scipy connected components), computing G_mean, G/G₀, ΔG/G₀, and G/B metrics from camera images; achieved G/B calibration R² = 0.911 (p = 0.012) for polystyrene in milk.

- Achieved **0.3% blind-prediction error** (129.6 ppm predicted vs 130 ppm actual) for unknown polystyrene concentration in milk, validating the complete hardware–software pipeline end to end.

- Designed a **lightweight deep learning architecture** (MobileNetV2 + Context Attention Block + Multi-Scale Feature Fusion Block, ~0.9 M parameters) achieving 98.2% validation accuracy on medical image classification benchmarks; architecture prepared for fluorescence dataset training and TFLite deployment on Raspberry Pi.

- Implemented **ratiometric G/B fluorescence quantification** — cancels UV scatter, camera exposure drift, and strip-to-strip loading variability — following the precedent of Li et al. (*Biosensors* 2022) extended to microplastic detection in food matrices.

---

### Skills Demonstrated (for skills section)

**Hardware:** Raspberry Pi 4B, GPIO programming, picamera2, PCB design (KiCad), MOSFET switching circuits, 1-Wire sensors (DS18B20), UV LED driver design

**Software:** Python 3, Streamlit, OpenCV, NumPy, SciPy, Pandas, Matplotlib, RPi.GPIO

**AI/ML:** TensorFlow 2.x, MobileNetV2, transfer learning, attention mechanisms, TFLite quantisation

**Chemistry:** Carbon dot synthesis, hydrothermal synthesis, fluorescence spectroscopy, Stern–Volmer quenching, ratiometric sensing, cellulose paper strip fabrication

**Tools:** KiCad, SSH/PuTTY, VNC, Git, Linux (Raspberry Pi OS), Anaconda

---

### GitHub Link (add after pushing)

`github.com/YOUR_USERNAME/spectrofluorometer`

---

### ATS-Friendly One-Paragraph Version

Designed and validated a low-cost portable spectrofluorometer for quantitative microplastic detection using a Raspberry Pi 4B, Pi Camera Module 3, and UV LEDs integrated on a custom KiCad PCB. Synthesised N-doped carbon dot probes and fabricated cellulose paper sensing strips; built a Python–Streamlit image analysis pipeline with automatic ROI detection and ratiometric G/B fluorescence quantification (R² = 0.911, p = 0.012 in milk matrix). Achieved 0.3% prediction error on a blind milk sample. Concurrently designed a MobileNetV2-based deep learning architecture (~0.9 M parameters, 98.2% validation accuracy) for future on-device concentration inference via TFLite on Raspberry Pi.
