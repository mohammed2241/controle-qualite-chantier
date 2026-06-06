import streamlit as st
import pandas as pd
from datetime import datetime
import json
import io
import base64
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image as RLImage, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Contrôle Qualité Chantier",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
  :root {
    --accent: #1D9E75;
    --accent-light: #E1F5EE;
    --accent-dark: #085041;
    --amber: #BA7517;
    --amber-light: #FAEEDA;
    --danger: #A32D2D;
    --danger-light: #FCEBEB;
  }
  .main-header {
    background: linear-gradient(135deg, #085041 0%, #1D9E75 100%);
    color: white; padding: 1.2rem 1.5rem; border-radius: 12px;
    margin-bottom: 1.5rem; display: flex; align-items: center; gap: 12px;
  }
  .main-header h1 { color: white; font-size: 1.4rem; margin: 0; }
  .main-header p  { color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem; }
  .metric-card { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 10px; padding: 1rem; text-align: center; }
  .metric-card .num { font-size: 2rem; font-weight: 700; color: #1D9E75; }
  .metric-card .lbl { font-size: 0.8rem; color: #6c757d; }
  .remark-card { background: white; border: 1px solid #e9ecef; border-left: 4px solid #1D9E75; border-radius: 8px; padding: 1rem 1.2rem; margin-bottom: 0.8rem; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin-right: 4px; }
  .badge-imm  { background: #E6F1FB; color: #0C447C; }
  .badge-apt  { background: #f0f0f0; color: #444; }
  .badge-met  { background: #E1F5EE; color: #085041; }
  .badge-zone { background: #FAEEDA; color: #633806; }
  .section-header { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 2px solid #1D9E75; margin-bottom: 1rem; color: #085041; font-weight: 600; font-size: 1rem; }
  #MainMenu {visibility: hidden;} footer {visibility: hidden;} .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  STRUCTURE DES TRANCHES
# ─────────────────────────────────────────────
def build_structure():
    structure = {}

    # ── TRANCHE 3 — 10 immeubles A→J ──────────
    t3 = {}

    # A, J : Magasins + 3 niveaux, 2 apparts/étage
    for letter in ["A", "J"]:
        locs = ["Magasins (RDC)"]
        n = 1
        for etage in range(1, 4):
            for apt in range(1, 3):
                locs.append(f"Étage {etage} – Appt {n:02d}")
                n += 1
        locs.append("Parties communes")
        t3[f"Immeuble {letter}"] = locs

    # B, E, F, I : Magasins + 5 niveaux (3 étages ×3 appts + 2 étages ×2 appts)
    for letter in ["B", "E", "F", "I"]:
        locs = ["Magasins (RDC)"]
        n = 1
        for etage in range(1, 4):
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {n:02d}")
                n += 1
        for etage in range(4, 6):
            for apt in range(1, 3):
                locs.append(f"Étage {etage} – Appt {n:02d}")
                n += 1
        locs.append("Parties communes")
        t3[f"Immeuble {letter}"] = locs

    # C, D, G, H : Magasins + 5 niveaux (3×3 + 1×2 + 1×1)
    for letter in ["C", "D", "G", "H"]:
        locs = ["Magasins (RDC)"]
        n = 1
        for etage in range(1, 4):
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {n:02d}")
                n += 1
        for apt in range(1, 3):
            locs.append(f"Étage 4 – Appt {n:02d}")
            n += 1
        locs.append(f"Étage 5 – Appt {n:02d}")
        locs.append("Parties communes")
        t3[f"Immeuble {letter}"] = locs

    structure["Tranche 3"] = t3

    # ── TRANCHE 4 — 4 immeubles A→D ───────────
    t4 = {}

    # A, D : Magasins + 5 niveaux (3×3 + 2×2)
    for letter in ["A", "D"]:
        locs = ["Magasins (RDC)"]
        n = 1
        for etage in range(1, 4):
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {n:02d}")
                n += 1
        for etage in range(4, 6):
            for apt in range(1, 3):
                locs.append(f"Étage {etage} – Appt {n:02d}")
                n += 1
        locs.append("Parties communes")
        t4[f"Immeuble {letter}"] = locs

    # B, C : Magasins + 5 niveaux (3×3 + 1×2 + 1×1)
    for letter in ["B", "C"]:
        locs = ["Magasins (RDC)"]
        n = 1
        for etage in range(1, 4):
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {n:02d}")
                n += 1
        for apt in range(1, 3):
            locs.append(f"Étage 4 – Appt {n:02d}")
            n += 1
        locs.append(f"Étage 5 – Appt {n:02d}")
        locs.append("Parties communes")
        t4[f"Immeuble {letter}"] = locs

    structure["Tranche 4"] = t4

    # ── TRANCHE 5 — 20 immeubles A→T, 5 niveaux, 3 appts/étage ──
    t5 = {}
    for i in range(20):
        letter = chr(65 + i)
        locs = []
        n = 1
        for etage in range(1, 6):
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {n:02d}")
                n += 1
        locs.append("Parties communes")
        t5[f"Immeuble {letter}"] = locs
    structure["Tranche 5"] = t5

    return structure

STRUCTURE = build_structure()

METIERS = [
    ("🚪", "Menuiserie"),
    ("🪟", "Aluminium"),
    ("⚡", "Électricité"),
    ("🔧", "Plomberie"),
    ("🖌️", "Plâtrier & Biatrice"),
    ("🎨", "Peintre"),
    ("🧱", "Bardage"),
    ("⬛", "Carrelage"),
    ("🍽️", "Cuisine"),
    ("🪨", "Marbre"),
    ("❄️", "Climatisation"),
    ("🪞", "Miroir"),
    ("☔", "Étanchéité"),
    ("🛗", "Ascenseur"),
]

ZONES = [
    "— Zone optionnelle —",
    "Cuisine",
    "Salon",
    "Chambre 1",
    "Chambre 2",
    "Suite parentale",
    "Lave-mains",
    "Salle de bain",
    "Salle de bain suite parentale",
    "Terrasse",
    "Couloir / Dégagement",
    "Balcon",
    "Façade extérieure",
    "Toiture",
    "Parking / Sous-sol",
    "Parties communes",
    "Cage d'escalier",
]

PRIORITES = {"🔴 Urgent": "Urgent", "🟡 Normal": "Normal", "🟢 Mineur": "Mineur"}

# ─────────────────────────────────────────────
#  GOOGLE SHEETS — photos en base64 dans Sheet
# ─────────────────────────────────────────────
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_or_create_sheet():
    client = get_gspread_client()
    sheet_id = st.secrets["SHEET_ID"]
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet("Remarques")
        # Vérifie que les en-têtes sont corrects, sinon les recrée
        headers = ws.row_values(1)
        expected = ["ID", "Date", "Heure", "Tranche", "Immeuble", "Local",
                    "Zone", "Metier", "Priorite", "Designation",
                    "Commentaire", "Photos_B64", "Nb_Photos", "Saisi_par"]
        if not headers or headers[0] != "ID":
            ws.insert_row(expected, 1)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet("Remarques", rows=5000, cols=14)
        ws.append_row(["ID", "Date", "Heure", "Tranche", "Immeuble", "Local",
                       "Zone", "Metier", "Priorite", "Designation",
                       "Commentaire", "Photos_B64", "Nb_Photos", "Saisi_par"])
    return ws

def image_to_base64(img_bytes: bytes, max_size: int = 600) -> str:
    """Resize + compress image and return base64 string (max ~30KB)."""
    img = Image.open(io.BytesIO(img_bytes))
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=45)
    # Si encore trop grand, réduire davantage
    if buf.tell() > 30000:
        buf = io.BytesIO()
        img.thumbnail((400, 400), Image.LANCZOS)
        img.save(buf, format="JPEG", quality=35)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def save_remark_to_sheet(row_data: dict):
    ws = get_or_create_sheet()
    # Chaque photo JPEG 800px ~ 30-50KB en base64. On limite à 1 photo si trop grand
    photos_b64 = row_data.get("photos_b64", "")
    parts = [p for p in photos_b64.split("||") if p.strip()]
    # Garder au max ce qui tient dans 49000 chars (limite cellule Google Sheets)
    kept = []
    total = 0
    for p in parts:
        if total + len(p) < 49000:
            kept.append(p)
            total += len(p)
        else:
            break
    photos_b64_safe = "||".join(kept)
    ws.append_row([
        row_data.get("id", ""),
        row_data.get("date", ""),
        row_data.get("heure", ""),
        row_data.get("tranche", ""),
        row_data.get("immeuble", ""),
        row_data.get("local", ""),
        row_data.get("zone", ""),
        row_data.get("metier", ""),
        row_data.get("priorite", ""),
        row_data.get("designation", ""),
        row_data.get("commentaire", ""),
        photos_b64_safe,
        len(kept),
        row_data.get("saisi_par", "—"),
    ])

@st.cache_data(ttl=30)
def load_remarks_from_sheet():
    ws = get_or_create_sheet()
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    # Normalize column names — map whatever is in Sheet to standard names
    col_map = {
        # Noms de colonnes possibles → noms standards utilisés dans le code
        "Metier": "Métier", "métier": "Métier", "METIER": "Métier",
        "Priorite": "Priorité", "priorité": "Priorité", "PRIORITE": "Priorité",
        "Designation": "Désignation", "désignation": "Désignation", "DESIGNATION": "Désignation",
        "Commentaire": "Commentaire",
        "Saisi_par": "Saisi_par", "saisi_par": "Saisi_par",
        # Toutes les variantes possibles du champ photos
        "Photos_URLs": "Photos_B64",
        "Photos_URL": "Photos_B64",
        "Photos_Base64": "Photos_B64",
        "photos_b64": "Photos_B64",
        "Photos_b64": "Photos_B64",
        "PHOTOS": "Photos_B64",
        # Nb photos
        "Nb_photos": "Nb_Photos", "nb_photos": "Nb_Photos", "NB_PHOTOS": "Nb_Photos",
    }
    df = df.rename(columns=col_map)
    # Ensure all expected columns exist
    for col in ["Métier", "Priorité", "Désignation", "Commentaire",
                "Photos_B64", "Nb_Photos", "Saisi_par", "Zone",
                "Tranche", "Immeuble", "Local", "Date", "Heure"]:
        if col not in df.columns:
            df[col] = ""
    return df

# ─────────────────────────────────────────────
#  GÉNÉRATION PDF avec reportlab
# ─────────────────────────────────────────────
def generate_pdf_report(df: pd.DataFrame, filters: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=1.8*cm, leftMargin=1.8*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title="Rapport Contrôle Qualité",
    )

    W, H = A4
    styles = getSampleStyleSheet()

    # Styles personnalisés
    title_style = ParagraphStyle("title", parent=styles["Title"],
        fontSize=16, textColor=colors.HexColor("#085041"),
        spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("subtitle", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#555555"),
        spaceAfter=2, alignment=TA_CENTER)
    metier_style = ParagraphStyle("metier", parent=styles["Heading2"],
        fontSize=12, textColor=colors.white,
        spaceAfter=0, spaceBefore=0, leading=16)
    label_style = ParagraphStyle("label", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#666666"),
        spaceAfter=1)
    value_style = ParagraphStyle("value", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=2)
    comment_style = ParagraphStyle("comment", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#333333"),
        spaceAfter=4, leading=13)
    footer_style = ParagraphStyle("footer", parent=styles["Normal"],
        fontSize=7, textColor=colors.HexColor("#aaaaaa"), alignment=TA_CENTER)

    ACCENT     = colors.HexColor("#1D9E75")
    ACCENT_BG  = colors.HexColor("#E1F5EE")
    DARK       = colors.HexColor("#085041")
    AMBER      = colors.HexColor("#BA7517")
    AMBER_BG   = colors.HexColor("#FAEEDA")
    RED        = colors.HexColor("#A32D2D")
    RED_BG     = colors.HexColor("#FCEBEB")
    GRAY_BG    = colors.HexColor("#f5f5f5")

    PRIO_COLOR = {"Urgent": (RED, RED_BG), "Normal": (AMBER, AMBER_BG), "Mineur": (ACCENT, ACCENT_BG)}

    story = []

    # ── En-tête ────────────────────────────────
    header_data = [[
        Paragraph("<b>RAPPORT CONTRÔLE QUALITÉ CHANTIER</b>", title_style),
    ]]
    header_table = Table(header_data, colWidths=[W - 3.6*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))

    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    story.append(Paragraph(f"Généré le {date_str}", subtitle_style))
    story.append(Spacer(1, 4))

    # Filtres appliqués
    filter_parts = []
    if filters.get("tranche") and filters["tranche"] != "Toutes":
        filter_parts.append(f"Tranche : {filters['tranche']}")
    if filters.get("immeuble") and filters["immeuble"] != "Tous":
        filter_parts.append(f"Immeuble : {filters['immeuble']}")
    if filters.get("metier") and filters["metier"] != "Tous":
        filter_parts.append(f"Métier : {filters['metier']}")
    if filter_parts:
        story.append(Paragraph("Filtres : " + "  |  ".join(filter_parts), subtitle_style))

    story.append(Spacer(1, 8))

    # ── KPIs ───────────────────────────────────
    nb_urgent = len(df[df.get("Priorité", pd.Series(dtype=str)) == "Urgent"]) if "Priorité" in df.columns else 0
    kpi_data = [[
        Paragraph(f"<b>{len(df)}</b><br/><font size='7' color='#666'>Total remarques</font>", value_style),
        Paragraph(f"<b>{df['Immeuble'].nunique() if 'Immeuble' in df.columns else 0}</b><br/><font size='7' color='#666'>Immeubles</font>", value_style),
        Paragraph(f"<b>{df['Métier'].nunique() if 'Métier' in df.columns else 0}</b><br/><font size='7' color='#666'>Corps de métier</font>", value_style),
        Paragraph(f"<b><font color='#A32D2D'>{nb_urgent}</font></b><br/><font size='7' color='#666'>Urgentes</font>", value_style),
    ]]
    kpi_table = Table(kpi_data, colWidths=[(W - 3.6*cm)/4]*4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), GRAY_BG),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#dddddd")),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT))
    story.append(Spacer(1, 10))

    # ── Remarques groupées par métier ──────────
    metiers_present = df["Métier"].dropna().unique() if "Métier" in df.columns else []

    for metier in sorted(metiers_present):
        sub = df[df["Métier"] == metier]

        # Titre du métier
        met_cell = Table([[Paragraph(f"  {metier}  —  {len(sub)} remarque(s)", metier_style)]],
                         colWidths=[W - 3.6*cm])
        met_cell.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), DARK),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("ROUNDEDCORNERS", [4]),
        ]))
        story.append(met_cell)
        story.append(Spacer(1, 6))

        for _, row in sub.iterrows():
            prio = str(row.get("Priorité", "Normal"))
            prio_fg, prio_bg = PRIO_COLOR.get(prio, (ACCENT, ACCENT_BG))

            # Ligne badges
            badge_data = [[
                Paragraph(f"<b>{row.get('Tranche','')}</b>", ParagraphStyle("b", parent=label_style, textColor=colors.HexColor("#0C447C"), fontSize=8)),
                Paragraph(f"<b>{row.get('Immeuble','')}</b>", ParagraphStyle("b", parent=label_style, textColor=colors.HexColor("#0C447C"), fontSize=8)),
                Paragraph(str(row.get("Local","")), ParagraphStyle("b", parent=label_style, fontSize=8)),
                Paragraph(str(row.get("Zone","")) if row.get("Zone","") else "", ParagraphStyle("b", parent=label_style, textColor=colors.HexColor("#633806"), fontSize=8)),
                Paragraph(f"<b>{prio}</b>", ParagraphStyle("b", parent=label_style, textColor=prio_fg, fontSize=8, alignment=TA_RIGHT)),
                Paragraph(f"{row.get('Date','')} {row.get('Heure','')}", ParagraphStyle("b", parent=label_style, textColor=colors.HexColor("#888888"), fontSize=7, alignment=TA_RIGHT)),
            ]]
            cw = (W - 3.6*cm)
            badge_t = Table(badge_data, colWidths=[cw*0.1, cw*0.12, cw*0.22, cw*0.24, cw*0.15, cw*0.17])
            badge_t.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,-1), GRAY_BG),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("LEFTPADDING",   (0,0), (-1,-1), 5),
                ("RIGHTPADDING",  (0,0), (-1,-1), 5),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ]))

            # Désignation + commentaire
            desig = Paragraph(f"<b>{row.get('Désignation','')}</b>", value_style)
            comm_text = str(row.get("Commentaire","")).strip()
            commentaire_p = Paragraph(comm_text if comm_text else "—", comment_style) if comm_text else None

            saisi = Paragraph(f"Saisi par : {row.get('Saisi_par','—')}", label_style)

            block = [badge_t, Spacer(1,4), desig]
            if commentaire_p:
                block.append(commentaire_p)

            # Photos base64
            photos_b64_raw = str(row.get("Photos_B64", "")).strip()
            if photos_b64_raw and photos_b64_raw != "nan":
                b64_list = [p.strip() for p in photos_b64_raw.split("||") if p.strip()]
                if b64_list:
                    photo_cells = []
                    for b64str in b64_list[:4]:  # max 4 photos par remarque
                        try:
                            img_data = base64.b64decode(b64str)
                            img_buf = io.BytesIO(img_data)
                            rl_img = RLImage(img_buf, width=3.5*cm, height=3.5*cm)
                            rl_img.hAlign = "LEFT"
                            photo_cells.append(rl_img)
                        except Exception:
                            pass
                    if photo_cells:
                        # Remplir jusqu'à 4 colonnes
                        while len(photo_cells) < 4:
                            photo_cells.append(Paragraph("", label_style))
                        photo_table = Table([photo_cells], colWidths=[(W - 3.6*cm)/4]*4)
                        photo_table.setStyle(TableStyle([
                            ("VALIGN", (0,0), (-1,-1), "TOP"),
                            ("LEFTPADDING",   (0,0), (-1,-1), 2),
                            ("RIGHTPADDING",  (0,0), (-1,-1), 2),
                            ("TOPPADDING",    (0,0), (-1,-1), 4),
                            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                        ]))
                        block.append(photo_table)

            block.append(saisi)

            # Encadrement complet de la remarque
            remark_table = Table([[item] for item in block], colWidths=[W - 3.6*cm])
            remark_table.setStyle(TableStyle([
                ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#cccccc")),
                ("LEFTPADDING",   (0,0), (-1,-1), 8),
                ("RIGHTPADDING",  (0,0), (-1,-1), 8),
                ("TOPPADDING",    (0,0), (0,0), 0),
                ("BOTTOMPADDING", (0,-1), (-1,-1), 6),
                ("BACKGROUND", (0,-1), (-1,-1), colors.white),
            ]))

            story.append(KeepTogether([remark_table, Spacer(1, 6)]))

        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#dddddd")))
        story.append(Spacer(1, 8))

    # ── Pied de page ───────────────────────────
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Rapport généré automatiquement — Portail Contrôle Qualité Chantier — {date_str}",
        footer_style
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0;'>
        <div style='font-size:2.5rem'>🏗️</div>
        <div style='font-weight:700; font-size:1rem; color:#085041;'>Contrôle Qualité</div>
        <div style='font-size:0.75rem; color:#888;'>Chantier – Suivi des remarques</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    page = st.radio("Navigation", ["📋 Saisie remarque", "📊 Rapport / Consultation", "📤 Export PDF"], label_visibility="collapsed")
    st.divider()
    st.markdown("<div style='font-size:0.75rem;color:#888;'>Saisi par :</div>", unsafe_allow_html=True)
    user_name = st.text_input("", placeholder="Votre nom", label_visibility="collapsed")

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class='main-header'>
    <div style='font-size:2rem'>🏗️</div>
    <div>
        <h1>Portail Contrôle Qualité</h1>
        <p>Saisie, suivi et rapport des remarques qualité par métier</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  PAGE 1 — SAISIE
# ══════════════════════════════════════════════
if page == "📋 Saisie remarque":
    st.markdown("<div class='section-header'>📋 Nouvelle remarque qualité</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        tranche = st.selectbox("Tranche", list(STRUCTURE.keys()))
    with col2:
        immeubles = list(STRUCTURE[tranche].keys())
        immeuble = st.selectbox("Immeuble", immeubles)
    with col3:
        locals_list = STRUCTURE[tranche][immeuble]
        local = st.selectbox("Local / Appartement", locals_list)

    col4, col5, col6 = st.columns(3)
    with col4:
        zone_raw = st.selectbox("Zone (optionnel)", ZONES)
        zone = "" if zone_raw == ZONES[0] else zone_raw
    with col5:
        metier_labels = [f"{icon} {name}" for icon, name in METIERS]
        metier_sel = st.selectbox("Corps de métier *", metier_labels)
        metier = metier_sel.split(" ", 1)[1]
    with col6:
        priorite_raw = st.selectbox("Priorité", list(PRIORITES.keys()))
        priorite = PRIORITES[priorite_raw]

    designation = st.text_input("Désignation / Nature du défaut *",
        placeholder="Ex : Fissure au plafond, joint manquant, prise non fonctionnelle…")
    commentaire = st.text_area("Commentaire détaillé",
        placeholder="Décrivez précisément le problème, son emplacement, son état…",
        height=100)

    st.markdown("**📷 Photos**")
    photos_uploaded = st.file_uploader(
        "Ajouter des photos (galerie ou appareil photo)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Sur mobile, vous pouvez prendre une photo directement depuis l'appareil.",
    )

    if photos_uploaded:
        cols = st.columns(min(len(photos_uploaded), 4))
        for i, photo in enumerate(photos_uploaded):
            with cols[i % 4]:
                img = Image.open(photo)
                st.image(img, use_container_width=True)

    st.divider()

    if st.button("💾 Enregistrer la remarque", type="primary", use_container_width=True):
        if not designation.strip():
            st.error("⚠️ La désignation est obligatoire.")
        else:
            with st.spinner("Enregistrement en cours…"):
                now = datetime.now()
                remark_id = now.strftime("%Y%m%d%H%M%S")

                # Encode photos en base64 séparées par "||"
                b64_parts = []
                if photos_uploaded:
                    for photo in photos_uploaded:
                        try:
                            b64 = image_to_base64(photo.getvalue())
                            b64_parts.append(b64)
                        except Exception as e:
                            st.warning(f"Photo ignorée : {e}")

                row = {
                    "id": remark_id,
                    "date": now.strftime("%d/%m/%Y"),
                    "heure": now.strftime("%H:%M"),
                    "tranche": tranche,
                    "immeuble": immeuble,
                    "local": local,
                    "zone": zone,
                    "metier": metier,
                    "priorite": priorite,
                    "designation": designation.strip(),
                    "commentaire": commentaire.strip(),
                    "photos_b64": "||".join(b64_parts),
                    "nb_photos": len(b64_parts),
                    "saisi_par": user_name.strip() if user_name else "—",
                }
                try:
                    save_remark_to_sheet(row)
                    load_remarks_from_sheet.clear()
                    st.success(f"✅ Remarque enregistrée avec succès dans Google Sheets ! ({len(b64_parts)} photo(s))")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erreur Google Sheets : {e}")


# ══════════════════════════════════════════════
#  PAGE 2 — RAPPORT / CONSULTATION
# ══════════════════════════════════════════════
elif page == "📊 Rapport / Consultation":
    st.markdown("<div class='section-header'>📊 Rapport & Consultation</div>", unsafe_allow_html=True)

    try:
        df = load_remarks_from_sheet()
    except Exception as e:
        st.error(f"Impossible de charger les données : {e}")
        st.stop()

    if df.empty:
        st.info("Aucune remarque enregistrée pour le moment.")
        st.stop()

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_tranche = st.selectbox("Tranche", ["Toutes"] + sorted(df["Tranche"].dropna().unique().tolist()))
    with fc2:
        imm_opts = df["Immeuble"].dropna().unique().tolist() if f_tranche == "Toutes" \
                   else df[df["Tranche"] == f_tranche]["Immeuble"].dropna().unique().tolist()
        f_imm = st.selectbox("Immeuble", ["Tous"] + sorted(imm_opts))
    with fc3:
        f_metier = st.selectbox("Métier", ["Tous"] + sorted(df["Métier"].dropna().unique().tolist()))
    with fc4:
        f_prio = st.selectbox("Priorité", ["Toutes", "Urgent", "Normal", "Mineur"])

    f_search = st.text_input("🔍 Rechercher dans désignation / commentaire", "")

    dff = df.copy()
    if f_tranche != "Toutes":  dff = dff[dff["Tranche"] == f_tranche]
    if f_imm != "Tous":        dff = dff[dff["Immeuble"] == f_imm]
    if f_metier != "Tous":     dff = dff[dff["Métier"] == f_metier]
    if f_prio != "Toutes":     dff = dff[dff["Priorité"] == f_prio]
    if f_search:
        mask = (
            dff["Désignation"].str.contains(f_search, case=False, na=False) |
            dff["Commentaire"].str.contains(f_search, case=False, na=False)
        )
        dff = dff[mask]

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"<div class='metric-card'><div class='num'>{len(dff)}</div><div class='lbl'>Total remarques</div></div>", unsafe_allow_html=True)
    with k2:
        urgent = len(dff[dff["Priorité"] == "Urgent"]) if "Priorité" in dff.columns else 0
        st.markdown(f"<div class='metric-card'><div class='num' style='color:#A32D2D'>{urgent}</div><div class='lbl'>Urgentes</div></div>", unsafe_allow_html=True)
    with k3:
        st.markdown(f"<div class='metric-card'><div class='num'>{dff['Immeuble'].nunique()}</div><div class='lbl'>Immeubles</div></div>", unsafe_allow_html=True)
    with k4:
        st.markdown(f"<div class='metric-card'><div class='num'>{dff['Métier'].nunique()}</div><div class='lbl'>Corps de métier</div></div>", unsafe_allow_html=True)
    with k5:
        nb_photos_col = dff["Nb_Photos"] if "Nb_Photos" in dff.columns else pd.Series([0]*len(dff))
        with_photos = nb_photos_col.apply(lambda x: int(str(x)) > 0 if str(x).strip().isdigit() else False).sum()
        st.markdown(f"<div class='metric-card'><div class='num'>{with_photos}</div><div class='lbl'>Avec photos</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if dff.empty:
        st.warning("Aucune remarque ne correspond aux filtres sélectionnés.")
    else:
        for met in sorted(dff["Métier"].dropna().unique()):
            sub = dff[dff["Métier"] == met]
            with st.expander(f"**{met}** — {len(sub)} remarque(s)", expanded=True):
                for _, row in sub.iterrows():
                    prio = row.get("Priorité", "Normal")
                    prio_color = {"Urgent": "#A32D2D", "Normal": "#BA7517", "Mineur": "#1D9E75"}.get(prio, "#888")
                    st.markdown(f"""
                    <div class='remark-card'>
                      <div style='margin-bottom:6px'>
                        <span class='badge badge-imm'>{row.get('Tranche','')}</span>
                        <span class='badge badge-imm'>{row.get('Immeuble','')}</span>
                        <span class='badge badge-apt'>{row.get('Local','')}</span>
                        {f"<span class='badge badge-zone'>{row.get('Zone','')}</span>" if row.get('Zone','') else ""}
                        <span style='float:right;font-size:0.75rem;color:#888'>{row.get('Date','')} {row.get('Heure','')}</span>
                        <span class='badge' style='background:{prio_color}20;color:{prio_color};float:right;margin-right:8px'>{prio}</span>
                      </div>
                      <div style='font-weight:600;font-size:0.95rem;margin-bottom:4px'>{row.get('Désignation','')}</div>
                      <div style='font-size:0.87rem;color:#444;line-height:1.5'>{row.get('Commentaire','')}</div>
                      <div style='font-size:0.75rem;color:#aaa;margin-top:6px'>Saisi par : {row.get('Saisi_par','—')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Afficher les photos base64
                    photos_raw = str(row.get("Photos_B64", "")).strip()
                    if photos_raw and photos_raw not in ("", "nan"):
                        b64_list = [p.strip() for p in photos_raw.split("||") if p.strip()]
                        if b64_list:
                            pcols = st.columns(min(len(b64_list), 4))
                            for i, b64 in enumerate(b64_list[:4]):
                                with pcols[i]:
                                    try:
                                        img_data = base64.b64decode(b64)
                                        img = Image.open(io.BytesIO(img_data))
                                        st.image(img, use_container_width=True)
                                    except Exception:
                                        pass
                    st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #f0f0f0'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  PAGE 3 — EXPORT PDF
# ══════════════════════════════════════════════
elif page == "📤 Export PDF":
    st.markdown("<div class='section-header'>📤 Export du rapport en PDF</div>", unsafe_allow_html=True)

    try:
        df = load_remarks_from_sheet()
    except Exception as e:
        st.error(f"Impossible de charger les données : {e}")
        st.stop()

    if df.empty:
        st.info("Aucune donnée à exporter.")
        st.stop()

    st.markdown("Sélectionnez un filtre (optionnel) avant de générer le PDF :")

    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        ef_tranche = st.selectbox("Tranche", ["Toutes"] + sorted(df["Tranche"].dropna().unique().tolist()), key="ef_tranche")
    with ec2:
        ef_imm = st.selectbox("Immeuble", ["Tous"] + sorted(df["Immeuble"].dropna().unique().tolist()), key="ef_imm")
    with ec3:
        ef_met = st.selectbox("Métier", ["Tous"] + sorted(df["Métier"].dropna().unique().tolist()), key="ef_met")

    dfe = df.copy()
    if ef_tranche != "Toutes": dfe = dfe[dfe["Tranche"] == ef_tranche]
    if ef_imm != "Tous":       dfe = dfe[dfe["Immeuble"] == ef_imm]
    if ef_met != "Tous":       dfe = dfe[dfe["Métier"] == ef_met]

    st.markdown(f"**{len(dfe)} remarques** correspondent à votre sélection.")

    include_photos = st.checkbox("Inclure les photos dans le PDF", value=True)

    if st.button("📄 Générer le rapport PDF", type="primary", use_container_width=True):
        with st.spinner("Génération du PDF en cours…"):
            df_for_pdf = dfe.copy()
            if not include_photos:
                df_for_pdf["Photos_Base64"] = ""
            try:
                pdf_bytes = generate_pdf_report(df_for_pdf, {
                    "tranche": ef_tranche, "immeuble": ef_imm, "metier": ef_met
                })
                filename = f"rapport_qualite_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                st.download_button(
                    "⬇️ Télécharger le rapport PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success("✅ PDF généré avec succès !")
            except Exception as e:
                st.error(f"Erreur lors de la génération du PDF : {e}")
