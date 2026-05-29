import streamlit as st
from PIL import Image
from google import genai
import json
import asyncio
import sys

# --- CORRECTIF WINDOWS ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- CONFIGURATION DE LA PAGE AVEC UN THEME ÉPURÉ ---
st.set_page_config(
    page_title="Scanner 306 - Hub", 
    page_icon="🛡️", 
    layout="wide"  # Mode large pour faire un effet Dashboard
)

# --- STYLE CSS PERSONNALISÉ (Pour l'originalité) ---
# On injecte un peu de CSS pour modifier l'apparence des blocs et titres
st.markdown("""
    <style>
    .main-title {
        font-size: 2.8rem !important;
        font-weight: 800;
        background: linear-gradient(45deg, #FF4B4B, #FF8585);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .custom-card {
        border-radius: 10px;
        padding: 15px;
        background-color: #f0f2f6;
        margin-bottom: 10px;
        border-left: 5px solid #FF4B4B;
    }
    </style>
""", unsafe_allowed_html=True)

# En-tête original
st.markdown('<h1 class="main-title">🛡️ S.A.M. - Salle 306</h1>', unsafe_allowed_html=True)
st.caption("**Système d'Analyse et de Monitorage** | Bâtiment KB3 | Version Intelligente 2.0")

# --- INITIALISATION CLIENT GEMINI ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ Clé API Gemini manquante. Veuillez configurer le fichier `.streamlit/secrets.toml`.")
    st.stop()

# --- DISPOSITION EN COLONNES (Dashboard) ---
# On sépare l'écran en deux : à gauche les commandes, à droite les résultats
col_gauche, col_droite = st.columns([1, 2], gap="large")

with col_gauche:
    st.subheader("🎛️ Panneau de Contrôle")
    
    # Mode de sélection stylisé dans un bloc
    methode = st.pills(
        "Mode d'acquisition :",
        ["Prendre une photo", "Importer un fichier"],
        selection_mode="single",
        default="Prendre une photo"
    )
    
    image_source = None
    if methode == "Prendre une photo":
        image_source = st.camera_input("Déclencher la caméra")
    else:
        image_source = st.file_uploader("Fichier image (JPG/PNG)", type=["png", "jpg", "jpeg"])
        
    if image_source is not None:
        st.button("🔄 Forcer une ré-analyse", use_container_width=True)

# --- TRAITEMENT ET AFFICHAGE DES RÉSULTATS (Colonne Droite) ---
with col_droite:
    if image_source is None:
        # Message d'attente original avec une boîte d'info stylisée
        st.info("📌 **En attente de données.** Veuillez capturer ou importer une photo depuis le panneau de gauche pour lancer l'analyse automatique.")
    else:
        img = Image.open(image_source)
        
        with st.spinner("🧠 S.A.M. analyse la géométrie de la pièce et des objets..."):
            try:
                prompt = """
                Tu es un inspecteur de sécurité et un gestionnaire d'inventaire pour la salle 306 du bâtiment KB3.
                Analyse la photo et effectue deux tâches :
                1. SÉCURITÉ : Vérifie les règles (Max 9 personnes, max 8 étudiants, chaises bien positionnées, TV allumée, fenêtres fermées).
                2. INVENTAIRE : Identifie TOUS les objets importants visibles sur la photo. Pour chaque type d'objet unique trouvé, donne son utilisation/rôle standard dans cette salle de classe.

                Réponds UNIQUEMENT sous la forme d'un objet JSON strict avec cette structure exacte :
                {
                    "nb_personnes": <nombre entier>,
                    "incidents": [
                        {"type": "<Nom de l'incident>", "gravite": "<Critique> ou <Avertissement>", "description": "<Explication>"}
                    ],
                    "diagnostic_general": "<Synthèse en français>",
                    "catalogue_objets": [
                        {"objet": "<Nom de l'objet>", "quantite_visible": "<Nombre ou 'Plusieurs'>", "utilisation": "<Rôle de l'objet dans la salle 306>"}
                    ]
                }
                """
                
                response = client.models.generate_content(model='gemini-2.5-flash', contents=[img, prompt])
                texte_reponse = response.text.strip()
                if texte_reponse.startswith("```json"):
                    texte_reponse = texte_reponse.split("```json")[1].split("```")[0].strip()
                resultat = json.loads(texte_reponse)
                
            except Exception as e:
                st.error(f"❌ Erreur système : {e}")
                st.stop()

        # --- RECONSTRUCTION DE L'INTERFACE DE RÉSULTATS ---
        st.subheader("📊 Métriques & Diagnostics")
        
        # Affichage des jauges côte à côte
        m1, m2, m3 = st.columns(3)
        m1.metric("Humains détectés", f"{resultat['nb_personnes']} / 9")
        
        liste_incidents = resultat.get("incidents", [])
        m2.metric("Alertes actives", len(liste_incidents), delta="- OK" if len(liste_incidents)==0 else "+ Attention", delta_color="inverse")
        
        # Statut général de la salle
        statut_salle = "Conforme" if not liste_incidents else "Anomalie"
        m3.metric("Statut Pièce", statut_salle)

        st.divider()

        # Utilisation d'onglets (Tabs) pour organiser les données de manière moderne
        tab_rapport, tab_catalogue, tab_image = st.tabs([
            "📋 Rapport d'Incidents", 
            "🗂️ Inventaire des Objets", 
            "🖼️ Image Source"
        ])
        
        with tab_rapport:
            if not liste_incidents:
                st.success(f"🌱 **Aucune anomalie détectée :** {resultat['diagnostic_general']}")
            else:
                st.write("Les systèmes ont détecté les écarts de conformité suivants :")
                for inc in liste_incidents:
                    # Rendu sous forme de cartes d'incidents customisées
                    couleur_badge = "🔴" if inc["gravite"] == "Critique" else "🟡"
                    st.markdown(f"""
                    <div class="custom-card" style="border-left-color: {'#FF4B4B' if inc['gravite'] == 'Critique' else '#FFAA00'}">
                        <h4>{couleur_badge} {inc['type']} ({inc['gravite']})</h4>
                        <p style="margin:0; color:#333;">{inc['description']}</p>
                    </div>
                    """, unsafe_allowed_html=True)
                st.info(f"💡 **Note de l'inspecteur :** {resultat['diagnostic_general']}")

        with tab_catalogue:
            st.write("Équipements et infrastructures répertoriés en temps réel :")
            liste_objets = resultat.get("catalogue_objets", [])
            if liste_objets:
                st.dataframe(
                    liste_objets,
                    column_config={
                        "objet": "Équipement",
                        "quantite_visible": "Quantité",
                        "utilisation": "Rôle / Fonctionnalité"
                    },
                    hide_index=True,
                    use_container_width=True # Mis à jour pour occuper tout l'onglet
                )
            else:
                st.info("Aucun objet détecté dans le champ de vision.")

        with tab_image:
            st.image(img, caption="Cliché analysé par S.A.M.", width="stretch")
