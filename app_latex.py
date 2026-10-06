import io
import os
import subprocess
import tempfile
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="LaTeX Formula Studio",
    page_icon="📐",
    layout="wide"
)

# Header & Affiliation
st.title("📐 LaTeX Formula Studio")
st.markdown("**Kevin Bart** — *Department of Physics, University of Fribourg*")
st.caption("Live editor, preview, and high-resolution export for LaTeX formulas (Vector PDF, Transparent PNG, High-quality JPG).")

def get_latex_template(formula_code: str, line_width_cm: int) -> str:
    """Generates a standalone LaTeX document with a controlled line width."""
    return rf"""\documentclass[varwidth={line_width_cm}cm, 12pt]{{standalone}}
\usepackage{{amsmath}}
\usepackage{{amssymb}}
\usepackage{{bm}}
\begin{{document}}
{formula_code}
\end{{document}}
"""

def compile_latex(formula_code: str, dpi: int, transparent: bool, line_width_cm: int):
    """Compiles the LaTeX formula and returns binary data for PDF, PNG, and JPG."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "formula.tex")
        dvi_path = os.path.join(tmpdir, "formula.dvi")
        png_path = os.path.join(tmpdir, "formula.png")
        jpg_path = os.path.join(tmpdir, "formula.jpg")
        pdf_path = os.path.join(tmpdir, "formula.pdf")

        # 1. Write LaTeX source
        tex_content = get_latex_template(formula_code, line_width_cm)
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        # 2. DVI compilation (latex)
        res_latex = subprocess.run(
            ["latex", f"-output-directory={tmpdir}", "-interaction=nonstopmode", tex_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res_latex.returncode != 0:
            raise RuntimeError(f"LaTeX compilation failed:\n{res_latex.stdout}")

        # 3. Vector PDF compilation (pdflatex)
        res_pdf = subprocess.run(
            ["pdflatex", f"-output-directory={tmpdir}", "-interaction=nonstopmode", tex_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res_pdf.returncode != 0:
            raise RuntimeError(f"PDF generation failed:\n{res_pdf.stdout}")

        # 4. High-resolution PNG rendering (dvipng)
        bg_param = ["-bg", "Transparent"] if transparent else ["-bg", "rgb 1.0 1.0 1.0"]
        res_dvipng = subprocess.run(
            ["dvipng", "-D", str(dpi), "-T", "tight", *bg_param, "-o", png_path, dvi_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res_dvipng.returncode != 0:
            raise RuntimeError(f"dvipng rendering failed:\n{res_dvipng.stderr}")

        # 5. PNG to JPG conversion via temporary disk file
        with Image.open(png_path) as pil_img:
            pil_img.load()
            if pil_img.mode in ("RGBA", "LA", "P"):
                rgb_img = Image.new("RGB", pil_img.size, (255, 255, 255))
                alpha = pil_img.split()[-1] if "A" in pil_img.getbands() else None
                rgb_img.paste(pil_img, mask=alpha)
            else:
                rgb_img = pil_img.convert("RGB")

            rgb_img.save(jpg_path, format="JPEG", quality=98)

        # 6. Read binary outputs
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        with open(png_path, "rb") as f:
            png_bytes = f.read()

        with open(jpg_path, "rb") as f:
            jpg_bytes = f.read()

        return pdf_bytes, png_bytes, jpg_bytes

# --- Main Tabs ---
tab_editor, tab_guide = st.tabs(["✍️ Editor & Export", "📖 Syntax Guide & Examples"])

# ==========================================
# TAB 1: EDITOR & EXPORT
# ==========================================
with tab_editor:
    default_formula = r"""\begin{equation*}
    \delta(\theta_i) = 2 \arctan \left( \frac{\cos\theta_i \sqrt{n^2\sin^2\theta_i - 1}}{n \sin^2\theta_i} \right)
\end{equation*}"""

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        formula_input = st.text_area(
            "LaTeX Formula Code:",
            value=default_formula,
            height=150,
            help="Write your mathematical expression here. Refer to the second tab for syntax examples."
        )

        with st.expander("⚙️ Export & Formatting Settings", expanded=True):
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                line_width_cm = st.slider(
                    "Box Width (cm)",
                    min_value=6,
                    max_value=24,
                    value=10,
                    help="Adjust to bring the equation number closer or accommodate wide formulas."
                )
                transparent_png = st.checkbox("Transparent Background (PNG)", value=False)
            with s_col2:
                dpi_res = st.select_slider(
                    "Resolution (DPI)",
                    options=[150, 300, 600, 1200],
                    value=600,
                    help="600 DPI is recommended for high-quality printing and academic publications."
                )
                base_filename = st.text_input("Output Filename", value="formula")

    with col_right:
        if formula_input.strip():
            try:
                pdf_data, png_data, jpg_data = compile_latex(
                    formula_code=formula_input,
                    dpi=dpi_res,
                    transparent=transparent_png,
                    line_width_cm=line_width_cm
                )

                st.subheader("Render Preview")
                st.image(png_data, caption=f"Compiled Output ({dpi_res} DPI)", width="content")

                st.subheader("Download Options")
                btn_c1, btn_c2, btn_c3 = st.columns(3)
                with btn_c1:
                    st.download_button(
                        label="📄 PDF (Vector)",
                        data=pdf_data,
                        file_name=f"{base_filename}.pdf",
                        mime="application/pdf",
                        width="stretch"
                    )
                with btn_c2:
                    st.download_button(
                        label="🖼 PNG",
                        data=png_data,
                        file_name=f"{base_filename}.png",
                        mime="image/png",
                        type="primary",
                        width="stretch"
                    )
                with btn_c3:
                    st.download_button(
                        label="🖼 JPG",
                        data=jpg_data,
                        file_name=f"{base_filename}.jpg",
                        mime="image/jpeg",
                        width="stretch"
                    )

            except RuntimeError as err:
                st.error("LaTeX Compilation Error")
                st.code(str(err), language="text")

# ==========================================
# TAB 2: SYNTAX GUIDE & EXAMPLES
# ==========================================
with tab_guide:
    st.markdown("### Best Practices & Numbering Guide")
    st.info(
        "💡 **Recommended practice:** Use **`equation*`** by default to obtain a tightly cropped "
        "render without artificial whitespace. If you need a numbered equation, use **`\\tag{...}`** "
        "and adjust the **Box Width** slider to control the distance between the formula and its label."
    )

    st.markdown("---")

    # Example 1: Default unnumbered
    st.markdown("#### 1. Default Standard: Unnumbered Formula (`equation*`)")
    st.write(
        "Ideal for standalone figures, presentations, or documents where numbering is not required. "
        "The generated image closely fits the mathematical expression without extra white margins."
    )
    st.latex(r"\delta(\theta_i) = 2 \arctan \left( \frac{\cos\theta_i \sqrt{n^2\sin^2\theta_i - 1}}{n \sin^2\theta_i} \right)")
    st.code(
r"""\begin{equation*}
    \delta(\theta_i) = 2 \arctan \left( \frac{\cos\theta_i \sqrt{n^2\sin^2\theta_i - 1}}{n \sin^2\theta_i} \right)
\end{equation*}""",
        language="latex"
    )

    st.markdown("---")

    # Example 2: Explicit Tag with spacing
    st.markdown("#### 2. Adding an Explicit Equation Number (`\\tag{...}` + Box Width)")
    st.write(
        "To number your formula, use `\\tag{N}` (or `\\tag{2.1}`, `\\tag{*}`). "
        "Because `\\tag{}` pushes the label to the right margin in the exported document, use the **Box Width (cm)** slider "
        "to control the distance between the formula and its label."
    )
    st.latex(r"\delta(\theta_i) = 2 \arctan \left( \frac{\cos\theta_i \sqrt{n^2\sin^2\theta_i - 1}}{n \sin^2\theta_i} \right) \qquad \tag{1}")
    st.code(
r"""\begin{equation}
    \delta(\theta_i) = 2 \arctan \left( \frac{\cos\theta_i \sqrt{n^2\sin^2\theta_i - 1}}{n \sin^2\theta_i} \right) \tag{1}
\end{equation}""",
        language="latex"
    )
    st.caption("Tip: For short formulas, set Box Width to 8–10 cm. For wide formulas, set it to 12–16 cm.")

    st.markdown("---")

    # Example 3: Multi-line Systems with align*
    st.markdown("#### 3. Multi-line Systems & Alignments (`align*`)")
    st.write("Use `&` to define alignment anchors. You can selectively tag individual lines:")
    # Utilisation directe de align* supportée nativement par KaTeX avec \tag
    st.latex(r"""\begin{align*}
    S_0 &= |E_x|^2 + |E_y|^2 \qquad \tag{2a} \\
    S_1 &= |E_x|^2 - |E_y|^2 \qquad \tag{2b} \\
    S_2 &= 2\,\mathrm{Re}(E_x E_y^*) \qquad \tag{2c} \\
    S_3 &= 2\,\mathrm{Im}(E_x^* E_y^) \qquad \tag{2d}
\end{align*}""")
    st.code(
r"""\begin{align*}
    S_0 &= |E_x|^2 + |E_y|^2 \tag{2a} \\
    S_1 &= |E_x|^2 - |E_y|^2 \tag{2b} \\
    S_2 &= 2\,\mathrm{Re}(E_x E_y^*) \tag{2c} \\
    S_3 &= 2\,\mathrm{Im}(E_x^* E_y^) \tag{2d}
\end{align*}""",
        language="latex"
    )

    st.markdown("---")

    # Example 4: Matrices
    st.markdown("#### 4. Matrices and Piecewise Definitions")
    st.latex(r"""\mathbf{J} = \begin{pmatrix} E_x \\ E_y \end{pmatrix} = \begin{pmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{pmatrix} \begin{pmatrix} E_{x0} \\ E_{y0} \end{pmatrix}""")
    st.code(
r"""\begin{equation*}
    \mathbf{J} = \begin{pmatrix} E_x \\ E_y \end{pmatrix} = \begin{pmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{pmatrix} \begin{pmatrix} E_{x0} \\ E_{y0} \end{pmatrix}
\end{equation*}""",
        language="latex"
    )