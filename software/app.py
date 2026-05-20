"""
app.py
======
RGB Fluorescence Analyser — Streamlit web application.
Runs on Raspberry Pi OS or any PC on the same local network.

Launch:
    streamlit run app.py

Tabs:
    1. Calibration  — Upload known-concentration images, fit G/B and G/G₀ models
    2. Predict      — Upload unknown image, back-calculate concentration
    3. Data/Export  — Full results table + downloadable CSVs

Author: Amit Kumar (421CY5075), NIT Rourkela
"""

import streamlit as st
import numpy as np
import cv2
from PIL import Image
import pandas as pd
from scipy import ndimage, stats
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Constants ─────────────────────────────────────────────────────────────────
G0_DEFAULT   = 135.0   # Reference blank green-channel mean (fluorescence_0159.jpg)
ROI_MIN_FRAC = 0.01    # ROI must be > 1% of image area
ROI_MAX_FRAC = 0.30    # ROI must be < 30% of image area
PERCENTILE   = 60      # Green-channel threshold percentile for ROI detection

st.set_page_config(
    page_title="RGB Fluorescence Analyser",
    page_icon="🔬",
    layout="wide",
)

st.title("🔬 RGB Fluorescence Analyser")
st.caption("AI-Integrated Portable Spectrofluorometer · NIT Rourkela · Amit Kumar (421CY5075)")

# ── Session state initialisation ──────────────────────────────────────────────
for key, default in [
    ("calibration_done", False),
    ("gb_model",  {"m": None, "b": None, "r2": None, "p": None}),
    ("gg0_model", {"m": None, "b": None, "r2": None, "p": None}),
    ("g0_used", G0_DEFAULT),
    ("cal_df", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helper functions ──────────────────────────────────────────────────────────
def load_image_rgb(uploaded_file):
    """Load uploaded file → RGB numpy array."""
    img = Image.open(uploaded_file).convert("RGB")
    return np.array(img)

def detect_roi(img_rgb):
    """
    Auto-detect fluorescent strip ROI using green-channel thresholding
    + connected-component analysis (largest bright region).
    Falls back to central 50% crop on failure.
    """
    g_channel = img_rgb[:, :, 1].astype(np.float32)
    threshold = np.percentile(g_channel, PERCENTILE)
    binary    = (g_channel > threshold).astype(np.uint8)

    labeled, n_features = ndimage.label(binary)
    if n_features == 0:
        return _center_crop(img_rgb), False

    sizes      = ndimage.sum(binary, labeled, range(1, n_features + 1))
    largest_id = int(np.argmax(sizes)) + 1
    mask       = (labeled == largest_id)

    h, w  = img_rgb.shape[:2]
    total = h * w
    frac  = mask.sum() / total

    if not (ROI_MIN_FRAC <= frac <= ROI_MAX_FRAC):
        return _center_crop(img_rgb), False

    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    roi  = img_rgb[rows[0]:rows[-1]+1, cols[0]:cols[-1]+1]
    return roi, True

def _center_crop(img_rgb):
    h, w = img_rgb.shape[:2]
    r0, r1 = h // 4, 3 * h // 4
    c0, c1 = w // 4, 3 * w // 4
    return img_rgb[r0:r1, c0:c1]

def compute_metrics(roi_rgb, g0):
    """Compute all four fluorescence metrics from ROI pixel data."""
    r = roi_rgb[:, :, 0].astype(np.float64)
    g = roi_rgb[:, :, 1].astype(np.float64)
    b = roi_rgb[:, :, 2].astype(np.float64)

    g_mean = float(np.mean(g))
    gg0    = g_mean / g0
    dgg0   = (g0 - g_mean) / g0
    gb     = float(np.sum(g) / np.sum(b)) if np.sum(b) > 0 else 0.0
    hex_c  = "#{:02X}{:02X}{:02X}".format(
        int(np.mean(r)), int(np.mean(g)), int(np.mean(b))
    )
    return {"G_mean": round(g_mean, 4),
            "G/G0":   round(gg0, 4),
            "dG/G0":  round(dgg0, 4),
            "G/B":    round(gb, 4),
            "hex":    hex_c}

def fit_linear(x, y):
    """OLS linear regression. Returns dict with m, b, r2, p."""
    slope, intercept, r, p, _ = stats.linregress(x, y)
    return {"m": round(slope, 8), "b": round(intercept, 6),
            "r2": round(r**2, 4), "p": round(p, 5)}

def df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")

def make_calibration_plot(concs, values, model, xlabel, ylabel, title, unknown=None):
    """Return matplotlib figure of calibration curve."""
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.scatter(concs, values, color="#2E86AB", s=60, zorder=5, label="Calibration points")

    x_line = np.linspace(0, max(concs) * 1.1, 200)
    y_line = model["m"] * x_line + model["b"]
    ax.plot(x_line, y_line, "--", color="#E84855", lw=1.5,
            label=f"{ylabel} = {model['m']:.6f}×C + {model['b']:.4f}\nR²={model['r2']}, p={model['p']}")

    if unknown is not None:
        unk_c, unk_v = unknown
        ax.scatter([unk_c], [unk_v], color="#F4A261", marker="*", s=200, zorder=6, label=f"Unknown ({unk_c:.1f} ppm)")
        ax.plot([unk_c, unk_c], [ax.get_ylim()[0], unk_v], ":", color="#F4A261", lw=1)
        ax.plot([0, unk_c], [unk_v, unk_v], ":", color="#F4A261", lw=1)

    ax.set_xlabel("Concentration (ppm)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs(["📊 Calibration", "🔍 Predict Unknown", "📋 Data & Export"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CALIBRATION
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.header("Calibration")
    st.markdown(
        "Upload your known-concentration fluorescence images. "
        "Type the polystyrene concentration (ppm) next to each image, then click **Run Calibration**."
    )

    g0_input = st.number_input(
        "Blank reference G₀ (green-channel mean of carbon-dot-only strip)",
        value=G0_DEFAULT, min_value=1.0, step=1.0,
        help="Default 135.0 from reference image fluorescence_0159.jpg"
    )

    uploaded_cal = st.file_uploader(
        "Upload calibration images (JPEG / PNG)",
        type=["jpg", "jpeg", "png", "bmp", "tiff"],
        accept_multiple_files=True,
        key="cal_uploader"
    )

    conc_map = {}
    if uploaded_cal:
        st.subheader("Assign concentrations")
        cols = st.columns(min(len(uploaded_cal), 4))
        for i, f in enumerate(uploaded_cal):
            with cols[i % 4]:
                img_rgb = load_image_rgb(f)
                roi, _ = detect_roi(img_rgb)
                st.image(roi, caption=f.name, use_column_width=True)
                conc_map[f.name] = st.number_input(
                    f"ppm — {f.name[:20]}",
                    min_value=0.0, value=0.0, step=10.0,
                    key=f"conc_{f.name}"
                )

    if st.button("🚀 Run Calibration", disabled=not uploaded_cal):
        rows = []
        for f in uploaded_cal:
            img_rgb = load_image_rgb(f)
            roi, auto = detect_roi(img_rgb)
            m = compute_metrics(roi, g0_input)
            m["filename"]    = f.name
            m["conc_ppm"]    = conc_map[f.name]
            m["roi_method"]  = "auto" if auto else "center_crop"
            rows.append(m)

        df = pd.DataFrame(rows)
        df = df.sort_values("conc_ppm").reset_index(drop=True)
        st.session_state["cal_df"]   = df
        st.session_state["g0_used"]  = g0_input

        concs = df["conc_ppm"].values.astype(float)
        gb_vals  = df["G/B"].values.astype(float)
        gg0_vals = df["G/G0"].values.astype(float)

        if len(concs) >= 2:
            st.session_state["gb_model"]  = fit_linear(concs, gb_vals)
            st.session_state["gg0_model"] = fit_linear(concs, gg0_vals)
            st.session_state["calibration_done"] = True

            c1, c2 = st.columns(2)
            gb  = st.session_state["gb_model"]
            gg0 = st.session_state["gg0_model"]

            with c1:
                st.success(f"**G/B model** · R²={gb['r2']} · p={gb['p']}")
                st.markdown(f"`G/B = {gb['m']}×C + {gb['b']}`")
                st.markdown(f"`C = (G/B − {gb['b']}) / {gb['m']}`")
                fig = make_calibration_plot(concs, gb_vals, gb,
                                            "Concentration (ppm)", "G/B ratio",
                                            "G/B Calibration Curve")
                st.pyplot(fig)

            with c2:
                st.success(f"**G/G₀ model** · R²={gg0['r2']} · p={gg0['p']}")
                st.markdown(f"`G/G₀ = {gg0['m']}×C + {gg0['b']}`")
                st.markdown(f"`C = (G/G₀ − {gg0['b']}) / {gg0['m']}`")
                fig = make_calibration_plot(concs, gg0_vals, gg0,
                                            "Concentration (ppm)", "G/G₀",
                                            "G/G₀ Calibration Curve")
                st.pyplot(fig)

            st.dataframe(df[["filename", "conc_ppm", "G_mean", "G/G0", "dG/G0", "G/B", "hex"]],
                         use_container_width=True)
        else:
            st.warning("Need at least 2 images to fit a calibration.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — PREDICT UNKNOWN
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.header("Predict Unknown Concentration")

    if not st.session_state["calibration_done"]:
        st.warning("Run calibration in Tab 1 first.")
    else:
        unk_file = st.file_uploader(
            "Upload unknown sample image",
            type=["jpg", "jpeg", "png", "bmp", "tiff"],
            key="unk_uploader"
        )

        if unk_file:
            img_rgb = load_image_rgb(unk_file)
            roi, auto = detect_roi(img_rgb)
            metrics   = compute_metrics(roi, st.session_state["g0_used"])

            gb  = st.session_state["gb_model"]
            gg0 = st.session_state["gg0_model"]

            c_gb  = (metrics["G/B"]  - gb["b"])  / gb["m"]  if gb["m"]  else None
            c_gg0 = (metrics["G/G0"] - gg0["b"]) / gg0["m"] if gg0["m"] else None

            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                st.image(roi, caption=f"ROI — {unk_file.name}", use_column_width=True)
            with col2:
                st.metric("G/B measured",  metrics["G/B"])
                st.metric("G/G₀ measured", metrics["G/G0"])
                st.metric("G_mean",        metrics["G_mean"])
            with col3:
                if c_gb is not None:
                    st.metric("🎯 Predicted C (G/B model)",  f"{c_gb:.2f} ppm")
                if c_gg0 is not None:
                    st.metric("🎯 Predicted C (G/G₀ model)", f"{c_gg0:.2f} ppm")

            # Show on calibration plot
            df = st.session_state["cal_df"]
            concs    = df["conc_ppm"].values.astype(float)
            gb_vals  = df["G/B"].values.astype(float)
            gg0_vals = df["G/G0"].values.astype(float)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if c_gb is not None:
                    fig = make_calibration_plot(concs, gb_vals, gb,
                                                "Concentration (ppm)", "G/B ratio",
                                                "G/B — Unknown Prediction",
                                                unknown=(c_gb, metrics["G/B"]))
                    st.pyplot(fig)
            with col_p2:
                if c_gg0 is not None:
                    fig = make_calibration_plot(concs, gg0_vals, gg0,
                                                "Concentration (ppm)", "G/G₀",
                                                "G/G₀ — Unknown Prediction",
                                                unknown=(c_gg0, metrics["G/G0"]))
                    st.pyplot(fig)

            # Step-by-step algebra
            with st.expander("Show calculation steps"):
                st.markdown(f"""
**G/B model:**
- Calibration: `G/B = {gb['m']} × C + {gb['b']}`
- Measured G/B = `{metrics['G/B']}`
- `C = ({metrics['G/B']} − {gb['b']}) / {gb['m']} = **{c_gb:.2f} ppm**`

**G/G₀ model:**
- Calibration: `G/G₀ = {gg0['m']} × C + {gg0['b']}`
- Measured G/G₀ = `{metrics['G/G0']}`
- `C = ({metrics['G/G0']} − {gg0['b']}) / {gg0['m']} = **{c_gg0:.2f} ppm**`
""")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — DATA & EXPORT
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.header("Data & Export")

    if st.session_state["cal_df"] is not None:
        df  = st.session_state["cal_df"]
        gb  = st.session_state["gb_model"]
        gg0 = st.session_state["gg0_model"]

        st.subheader("Calibration data")
        st.dataframe(df, use_container_width=True)

        # Residuals
        concs    = df["conc_ppm"].values.astype(float)
        gb_pred  = gb["m"]  * concs + gb["b"]
        gg0_pred = gg0["m"] * concs + gg0["b"]

        res_df = pd.DataFrame({
            "filename":       df["filename"],
            "conc_ppm":       concs,
            "G/B_actual":     df["G/B"],
            "G/B_predicted":  gb_pred.round(4),
            "G/B_residual":   (df["G/B"].values - gb_pred).round(4),
            "G/G0_actual":    df["G/G0"],
            "G/G0_predicted": gg0_pred.round(4),
            "G/G0_residual":  (df["G/G0"].values - gg0_pred).round(4),
        })
        st.subheader("Residuals")
        st.dataframe(res_df, use_container_width=True)

        d1, d2 = st.columns(2)
        with d1:
            st.download_button("⬇️ Download calibration CSV",
                               data=df_to_csv(df),
                               file_name="calibration_data.csv",
                               mime="text/csv")
        with d2:
            summary = pd.DataFrame([{
                "Model": "G/B",
                "Slope_m": gb["m"], "Intercept_b": gb["b"],
                "R2": gb["r2"], "p_value": gb["p"],
                "Equation": f"G/B = {gb['m']}*C + {gb['b']}",
                "Invert":   f"C = (G/B - {gb['b']}) / {gb['m']}",
                "G0": st.session_state["g0_used"],
            }, {
                "Model": "G/G0",
                "Slope_m": gg0["m"], "Intercept_b": gg0["b"],
                "R2": gg0["r2"], "p_value": gg0["p"],
                "Equation": f"G/G0 = {gg0['m']}*C + {gg0['b']}",
                "Invert":   f"C = (G/G0 - {gg0['b']}) / {gg0['m']}",
                "G0": st.session_state["g0_used"],
            }])
            st.download_button("⬇️ Download equations summary CSV",
                               data=df_to_csv(summary),
                               file_name="calibration_equations.csv",
                               mime="text/csv")
    else:
        st.info("Run calibration in Tab 1 to see data here.")

    st.divider()
    st.caption(
        "**References:** "
        "Stern & Volmer, *Physik. Z.* 1919, 20, 183 | "
        "Han et al., *Molecules* 2024, DOI: 10.3390/molecules29071658 | "
        "Permpool et al., *Microchemical Journal* 2025 | "
        "Li et al., *Biosensors* 2022, DOI: 10.3390/bios12080668"
    )
