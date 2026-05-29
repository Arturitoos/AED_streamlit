import streamlit as st
from PIL import Image
from google import genai
import json
import asyncio
import sys

# --- 1. CORRECTIF DE SÉCURITÉ WINDOWS (Pour éviter l'erreur WinError 10054) ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- 2. CONFIGURATION DE LA PAGE (Mode Dashboard Large) ---
st.set_page_config(
    page_title="S.A.M. - Salle 306", 
    page_icon="🛡️", 
    layout="wide"
)

# --- 3. STYLE CSS PERSONNALISÉ (Syntaxe moderne 2026 via st.html) ---
st.html("""
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
""")

# --- 4. EN-TÊTE DE L'INTERFACE ---
# À METTRE À LA PLACE :
st.html('<h1 class="main-title">🛡️ S.A.M. - Salle 306</h1>')
st.caption("**Système d'Analyse et de Monitorage** | Bâtiment KB3 | Version Intelligente 2.5-Flash")

# --- 5. ENREGISTREMENT SÉCURISÉ DE LA CLÉ API GEMINI ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ Clé API Gemini manquante. Veuillez vérifier la case 'Secrets' sur Streamlit Cloud ou votre fichier local `.streamlit/secrets.toml`.")
    st.stop()

# --- 6. ARCHITECTURE EN COLONNES (Panneau de commande à gauche, résultats à droite) ---
col_gauche, col_droite = st.columns([1, 2], gap="large")

with col_gauche:
    st.subheader("🎛️ Panneau de Contrôle")
    
    # Boutons de sélection modernes (Pilules)
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

# --- 7. LOGIQUE DE TRAITEMENT ET RENDU DES RÉSULTATS (Colonne Droite) ---
with col_droite:
    if image_source is None:
        st.info("📌 **En attente de données.** Veuillez capturer ou importer une photo depuis le panneau de gauche pour lancer l'analyse automatique.")
    else:
        img = Image.open(image_source)
        
        with st.spinner("🧠 S.A.M. analyse la salle et dresse l'inventaire..."):
            try:
                # Prompt d'ingénierie stricte pour forcer Gemini à répondre en JSON structuré
                prompt = """
                Tu es un inspecteur de sécurité et un gestionnaire d'inventaire pour la salle 306 du bâtiment KB3.
                Analyse la photo et effectue deux tâches :
                
                1. SÉCURITÉ : Vérifie les règles (Max 9 personnes au total, max 8 étudiants (1 par table), chaises bien positionnées, TV allumée si présente, fenêtres fermées).
                2. INVENTAIRE : Identifie TOUS les objets importants visibles sur la photo (ex: Table, Chaise, Télévision, Fenêtre, Ordinateur, Tableau, Sac). 
                   Pour chaque type d'objet unique trouvé, donne son utilisation/rôle standard dans cette salle de classe.

                Réponds UNIQUEMENT sous la forme d'un objet JSON strict avec cette structure exacte :
                {
                    "nb_personnes": <nombre entier>,
                    "incidents": [
                        {"type": "<Nom du type d'incident>", "gravite": "<Critique> ou <Avertissement>", "description": "<Explication courte>"}
                    ],
                    "diagnostic_general": "<Synthèse en français>",
                    "catalogue_objets": [
                        {"objet": "<Nom de l'objet>", "quantite_visible": "<Nombre ou 'Plusieurs'>", "utilisation": "<Rôle dans la salle 306>"}
                    ]
                }
                Les types d'incidents possibles sont uniquement : "Surcharge", "Manque de tables", "Non-respect du placement", "Chaise renversée", "TV éteinte", "Fenêtre ouverte".
                Si aucun incident n'est trouvé, laisse le tableau "incidents" vide [].
                """
                
                # Tentative principale avec Gemini 2.5 Flash
                try:
                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[img, prompt]
                    )
                except Exception as e:
                    # En cas de surcharge des serveurs Google (Erreur 503), bascule transparente sur le modèle 2.0
                    if "503" in str(e):
                        st.warning("⚠️ Modèle principal saturé, bascule automatique sur le modèle de secours...")
                        response = client.models.generate_content(
                            model='gemini-2.0-flash', 
                            contents=[img, prompt]
                        )
                    else:
                        raise e
                
                # Nettoyage et décodage du format JSON reçu par l'IA
                texte_reponse = response.text.strip()
                if texte_reponse.startswith("```json"):
                    texte_reponse = texte_reponse.split("```json")[1].split("```")[0].strip()
                    
                resultat = json.loads(texte_reponse)
                
            except Exception as e:
                st.error(f"❌ Erreur lors de la communication avec l'IA : {e}")
                st.info("💡 Cliquez sur 'Forcer une ré-analyse' pour retenter votre chance.")
                st.stop()

        st.success("✅ Analyse de l'environnement terminée !")
        
        # --- 8. SECTION DES MÉTRIQUES (Dashboard) ---
        st.subheader("📊 Métriques & Diagnostics")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Humains détectés", f"{resultat['nb_personnes']} / 9")
        
        liste_incidents = resultat.get("incidents", [])
        m2.metric(
            "Alertes actives", 
            len(liste_incidents), 
            delta="- OK" if len(liste_incidents) == 0 else "+ Attention", 
            delta_color="inverse"
        )
        
        statut_salle = "Conforme" if not liste_incidents else "Anomalie"
        m3.metric("Statut Pièce", statut_salle)

        st.divider()

        # --- 9. ORGANISATION EN ONGLETS MODÈRNES ---
        tab_rapport, tab_catalogue, tab_image = st.tabs([
            "📋 Rapport d'Incidents", 
            "🗂️ Inventaire des Objets", 
            "🖼️ Image Source"
        ])
        
        with tab_rapport:
            if not liste_incidents:
                st.success(f"🌱 **Aucune anomalie détectée :** {resultat['diagnostic_general']}")
            else:
                st.write("Les systèmes de vision ont détecté les écarts suivants :")
                for inc in liste_incidents:
                    # Rendu sécurisé des cartes d'incident sans risque de plantage HTML
                    couleur_badge = "🔴" if inc["gravite"] == "Critique" else "🟡"
                    st.html(f"""
                    <div class="custom-card" style="border-left-color: {'#FF4B4B' if inc['gravite'] == 'Critique' else '#FFAA00'}">
                        <h4 style="margin-top:0; margin-bottom:5px;">{couleur_badge} {inc['type']} ({inc['gravite']})</h4>
                        <p style="margin:0; color:#333; font-size:0.95rem;">{inc['description']}</p>
                    </div>
                    """)
                st.info(f"💡 **Note globale de synthèse :** {resultat['diagnostic_general']}")

        with tab_catalogue:
            st.write("Équipements et infrastructures répertoriés en direct sur la scène :")
            liste_objets = resultat.get("catalogue_objets", [])
            
            if liste_objets:
                st.dataframe(
                    liste_objets,
                    column_config={
                        "objet": "Équipement / Structure",
                        "quantite_visible": "Quantité détectée",
                        "utilisation": "Rôle / Fonctionnalité dans la salle"
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Aucun objet exploitable n'a été répertorié par le système.")

        with tab_image:
            st.image(img, caption="Cliché original transmis au système S.A.M.", width="stretch")
