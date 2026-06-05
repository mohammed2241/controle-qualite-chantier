import streamlit as st
import pandas as pd
from datetime import datetime
import json
import io
import base64
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

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
  /* Main palette */
  :root {
    --accent: #1D9E75;
    --accent-light: #E1F5EE;
    --accent-dark: #085041;
    --amber: #BA7517;
    --amber-light: #FAEEDA;
    --danger: #A32D2D;
    --danger-light: #FCEBEB;
  }

  /* Header */
  .main-header {
    background: linear-gradient(135deg, #085041 0%, #1D9E75 100%);
    color: white;
    padding: 1.2rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .main-header h1 { color: white; font-size: 1.4rem; margin: 0; }
  .main-header p  { color: rgba(255,255,255,0.8); margin: 0; font-size: 0.85rem; }

  /* Cards */
  .metric-card {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
  }
  .metric-card .num { font-size: 2rem; font-weight: 700; color: #1D9E75; }
  .metric-card .lbl { font-size: 0.8rem; color: #6c757d; }

  /* Remark card */
  .remark-card {
    background: white;
    border: 1px solid #e9ecef;
    border-left: 4px solid #1D9E75;
    border-radius: 8px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
  }
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 4px;
  }
  .badge-imm  { background: #E6F1FB; color: #0C447C; }
  .badge-apt  { background: #f0f0f0; color: #444; }
  .badge-met  { background: #E1F5EE; color: #085041; }
  .badge-zone { background: #FAEEDA; color: #633806; }

  /* Section title */
  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 0;
    border-bottom: 2px solid #1D9E75;
    margin-bottom: 1rem;
    color: #085041;
    font-weight: 600;
    font-size: 1rem;
  }

  /* Photo grid */
  .photo-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
  .photo-grid img {
    width: 80px; height: 80px;
    object-fit: cover;
    border-radius: 6px;
    border: 1px solid #dee2e6;
    cursor: pointer;
  }

  /* Hide Streamlit branding */
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  STRUCTURE DES TRANCHES / IMMEUBLES / APPARTS
# ─────────────────────────────────────────────
def build_structure():
    """
    Returns dict: tranche -> immeuble -> list of locals
    """
    structure = {}

    # ── TRANCHE 3 ─────────────────────────────
    t3 = {}
    # A-J : Magasins + 3 niveaux 2 appart/étage
    for letter in ["A", "J"]:
        imm = f"Immeuble {letter}"
        locs = ["Magasins (RDC)"]
        for etage in range(1, 4):
            for apt in range(1, 3):
                locs.append(f"Étage {etage} – Appt {letter}{etage:02d}{apt}")
        locs.append("Parties communes")
        t3[imm] = locs

    # B-E-F-I : Magasins + 5 niveaux (3×3 appts + 2×2 appts)
    for letter in ["B", "E", "F", "I"]:
        imm = f"Immeuble {letter}"
        locs = ["Magasins (RDC)"]
        for etage in range(1, 4):          # étages 1-3 : 3 appts
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {letter}{etage:02d}{apt}")
        for etage in range(4, 6):          # étages 4-5 : 2 appts
            for apt in range(1, 3):
                locs.append(f"Étage {etage} – Appt {letter}{etage:02d}{apt}")
        locs.append("Parties communes")
        t3[imm] = locs

    # C-D-G-H : Magasins + 5 niveaux (3×3 + 1×2 + 1×1)
    for letter in ["C", "D", "G", "H"]:
        imm = f"Immeuble {letter}"
        locs = ["Magasins (RDC)"]
        for etage in range(1, 4):          # 1-3 : 3 appts
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {letter}{etage:02d}{apt}")
        for apt in range(1, 3):            # 4ème : 2 appts
            locs.append(f"Étage 4 – Appt {letter}04{apt}")
        locs.append(f"Étage 5 – Appt {letter}051")   # 5ème : 1 appt
        locs.append("Parties communes")
        t3[imm] = locs

    structure["Tranche 3"] = t3

    # ── TRANCHE 4 ─────────────────────────────
    t4 = {}
    # A-D : Magasins + 5 niveaux (3×3 + 2×2)
    for letter in ["A", "D"]:
        imm = f"Immeuble {letter}"
        locs = ["Magasins (RDC)"]
        for etage in range(1, 4):
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {letter}{etage:02d}{apt}")
        for etage in range(4, 6):
            for apt in range(1, 3):
                locs.append(f"Étage {etage} – Appt {letter}{etage:02d}{apt}")
        locs.append("Parties communes")
        t4[imm] = locs

    # B-C : Magasins + 5 niveaux (3×3 + 1×2 + 1×1)
    for letter in ["B", "C"]:
        imm = f"Immeuble {letter}"
        locs = ["Magasins (RDC)"]
        for etage in range(1, 4):
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {letter}{etage:02d}{apt}")
        for apt in range(1, 3):
            locs.append(f"Étage 4 – Appt {letter}04{apt}")
        locs.append(f"Étage 5 – Appt {letter}051")
        locs.append("Parties communes")
        t4[imm] = locs

    structure["Tranche 4"] = t4

    # ── TRANCHE 5 ─────────────────────────────
    # 20 immeubles, 5 niveaux, 3 apparts/étage
    t5 = {}
    letters = [chr(65 + i) for i in range(20)]  # A-T
    for letter in letters:
        imm = f"Immeuble {letter}"
        locs = []
        for etage in range(1, 6):
            for apt in range(1, 4):
                locs.append(f"Étage {etage} – Appt {letter}{etage:02d}{apt}")
        locs.append("Parties communes")
        t5[imm] = locs
    structure["Tranche 5"] = t5

    return structure

STRUCTURE = build_structure()

METIERS = [
    ("🚪", "Menuiserie"),
    ("🪟", "Aluminium"),
    ("⚡", "Électricité"),
    ("🔧", "Plomberie"),
    ("🖌️", "Plâtrerie & Peinture"),
    ("🧱", "Bardage"),
    ("⬛", "Carrelage"),
    ("☔", "Étanchéité"),
    ("🏗️", "Gros œuvre"),
    ("🔒", "Serrurerie"),
    ("🪴", "Espaces verts"),
    ("🛗",  "Ascenseur"),
]

ZONES = [
    "— Zone optionnelle —",
    "Salon / Séjour", "Cuisine", "Chambre 1", "Chambre 2", "Chambre 3",
    "Salle de bain", "WC", "Couloir / Dégagement",
    "Balcon / Terrasse", "Façade extérieure", "Toiture",
    "Sous-sol / Cave", "Parking", "Parties communes", "Cage d'escalier",
]

PRIORITES = {"🔴 Urgent": "Urgent", "🟡 Normal": "Normal", "🟢 Mineur": "Mineur"}

# ─────────────────────────────────────────────
#  GOOGLE SHEETS / DRIVE CONNECTION
# ─────────────────────────────────────────────
@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds), creds

@st.cache_resource
def get_drive_service():
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return build("drive", "v3", credentials=creds)

def get_or_create_sheet():
    client, _ = get_gspread_client()
    sheet_id = st.secrets["SHEET_ID"]
    sh = client.open_by_key(sheet_id)
    try:
        ws = sh.worksheet("Remarques")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet("Remarques", rows=5000, cols=15)
        ws.append_row([
            "ID", "Date", "Heure", "Tranche", "Immeuble", "Local",
            "Zone", "Métier", "Priorité", "Désignation",
            "Commentaire", "Photos_URLs", "Saisi_par"
        ])
    return ws

def save_remark_to_sheet(row_data: dict):
    ws = get_or_create_sheet()
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
        row_data.get("photos_urls", ""),
        row_data.get("saisi_par", ""),
    ])

def load_remarks_from_sheet():
    ws = get_or_create_sheet()
    data = ws.get_all_records()
    return pd.DataFrame(data)

def upload_photo_to_drive(image_bytes: bytes, filename: str, folder_id: str) -> str:
    service = get_drive_service()
    file_meta = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype="image/jpeg")
    f = service.files().create(body=file_meta, media_body=media, fields="id").execute()
    file_id = f.get("id")
    # Make public
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()
    return f"https://drive.google.com/uc?export=view&id={file_id}"

# ─────────────────────────────────────────────
#  SIDEBAR NAVIGATION
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

    page = st.radio(
        "Navigation",
        ["📋 Saisie remarque", "📊 Rapport / Consultation", "📤 Export"],
        label_visibility="collapsed",
    )

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

    designation = st.text_input("Désignation / Nature du défaut *", placeholder="Ex: Fissure plafond, joint manquant, prise non fonctionnelle…")
    commentaire = st.text_area("Commentaire détaillé", placeholder="Décrivez précisément le problème, son emplacement, son état…", height=100)

    st.markdown("**📷 Photos**")
    photos_uploaded = st.file_uploader(
        "Ajouter des photos (depuis la galerie ou l'appareil photo)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="Sur mobile, vous pouvez prendre une photo directement.",
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
        elif not metier:
            st.error("⚠️ Choisissez un corps de métier.")
        else:
            with st.spinner("Enregistrement en cours…"):
                now = datetime.now()
                remark_id = now.strftime("%Y%m%d%H%M%S")

                # Upload photos to Drive
                photo_urls = []
                if photos_uploaded:
                    try:
                        folder_id = st.secrets["DRIVE_FOLDER_ID"]
                        for photo in photos_uploaded:
                            ext = photo.name.split(".")[-1]
                            fname = f"QC_{remark_id}_{photo.name}"
                            url = upload_photo_to_drive(photo.getvalue(), fname, folder_id)
                            photo_urls.append(url)
                    except Exception as e:
                        st.warning(f"Photos non uploadées (Drive): {e}")

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
                    "photos_urls": " | ".join(photo_urls),
                    "saisi_par": user_name.strip() if user_name else "—",
                }
                try:
                    save_remark_to_sheet(row)
                    st.success("✅ Remarque enregistrée avec succès dans Google Sheets !")
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

    # ── Filters ──────────────────────────────
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
    if f_tranche != "Toutes":   dff = dff[dff["Tranche"] == f_tranche]
    if f_imm != "Tous":         dff = dff[dff["Immeuble"] == f_imm]
    if f_metier != "Tous":      dff = dff[dff["Métier"] == f_metier]
    if f_prio != "Toutes":      dff = dff[dff["Priorité"] == f_prio]
    if f_search:
        mask = (
            dff["Désignation"].str.contains(f_search, case=False, na=False) |
            dff["Commentaire"].str.contains(f_search, case=False, na=False)
        )
        dff = dff[mask]

    # ── KPIs ─────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"<div class='metric-card'><div class='num'>{len(dff)}</div><div class='lbl'>Total remarques</div></div>", unsafe_allow_html=True)
    with k2:
        urgent = len(dff[dff["Priorité"] == "Urgent"]) if "Priorité" in dff.columns else 0
        st.markdown(f"<div class='metric-card'><div class='num' style='color:#A32D2D'>{urgent}</div><div class='lbl'>Urgentes</div></div>", unsafe_allow_html=True)
    with k3:
        nb_imm = dff["Immeuble"].nunique()
        st.markdown(f"<div class='metric-card'><div class='num'>{nb_imm}</div><div class='lbl'>Immeubles</div></div>", unsafe_allow_html=True)
    with k4:
        nb_met = dff["Métier"].nunique()
        st.markdown(f"<div class='metric-card'><div class='num'>{nb_met}</div><div class='lbl'>Corps de métier</div></div>", unsafe_allow_html=True)
    with k5:
        with_photos = dff["Photos_URLs"].apply(lambda x: bool(str(x).strip())).sum()
        st.markdown(f"<div class='metric-card'><div class='num'>{with_photos}</div><div class='lbl'>Avec photos</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Group by Métier ───────────────────────
    if dff.empty:
        st.warning("Aucune remarque ne correspond aux filtres sélectionnés.")
    else:
        metiers_in_df = sorted(dff["Métier"].dropna().unique())
        for met in metiers_in_df:
            sub = dff[dff["Métier"] == met]
            with st.expander(f"**{met}** — {len(sub)} remarque(s)", expanded=True):
                for _, row in sub.iterrows():
                    prio_color = {"Urgent": "#A32D2D", "Normal": "#BA7517", "Mineur": "#1D9E75"}.get(row.get("Priorité", ""), "#888")
                    prio_label = row.get("Priorité", "")
                    photos_urls_raw = str(row.get("Photos_URLs", "")).strip()
                    photo_list = [u.strip() for u in photos_urls_raw.split("|") if u.strip()] if photos_urls_raw else []

                    st.markdown(f"""
                    <div class='remark-card'>
                      <div style='margin-bottom:6px'>
                        <span class='badge badge-imm'>{row.get('Tranche','')}</span>
                        <span class='badge badge-imm'>{row.get('Immeuble','')}</span>
                        <span class='badge badge-apt'>{row.get('Local','')}</span>
                        {f"<span class='badge badge-zone'>{row.get('Zone','')}</span>" if row.get('Zone','') else ""}
                        <span style='margin-left:auto; float:right; font-size:0.75rem; color:#888'>{row.get('Date','')} {row.get('Heure','')}</span>
                        <span class='badge' style='background:{prio_color}20;color:{prio_color};float:right;margin-right:8px'>{prio_label}</span>
                      </div>
                      <div style='font-weight:600; font-size:0.95rem; margin-bottom:4px'>{row.get('Désignation','')}</div>
                      <div style='font-size:0.87rem; color:#444; line-height:1.5'>{row.get('Commentaire','')}</div>
                      <div style='font-size:0.75rem; color:#aaa; margin-top:6px'>Saisi par : {row.get('Saisi_par','—')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if photo_list:
                        cols = st.columns(min(len(photo_list), 4))
                        for i, url in enumerate(photo_list):
                            with cols[i % 4]:
                                st.image(url, width=120)

                    st.markdown("<hr style='margin:6px 0;border:none;border-top:1px solid #f0f0f0'>", unsafe_allow_html=True)


# ══════════════════════════════════════════════
#  PAGE 3 — EXPORT
# ══════════════════════════════════════════════
elif page == "📤 Export":
    st.markdown("<div class='section-header'>📤 Export des données</div>", unsafe_allow_html=True)

    try:
        df = load_remarks_from_sheet()
    except Exception as e:
        st.error(f"Impossible de charger les données : {e}")
        st.stop()

    if df.empty:
        st.info("Aucune donnée à exporter.")
        st.stop()

    # Filters for export
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

    # CSV download
    csv = dfe.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "⬇️ Télécharger en CSV",
        data=csv,
        file_name=f"rapport_qualite_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.dataframe(dfe, use_container_width=True)
