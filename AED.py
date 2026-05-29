import streamlit as st
from PIL import Image
from google import genai
import json
import asyncio
import sys

# --- CORRECTIF WINDOWS ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Configuration de la page
st.set_page_config(page_title="Inspecteur & Catalogue - Salle 306", page_icon="🏫", layout="centered")

st.title("🏫 Inspecteur Intelligent & Catalogue d'Objets")
st.caption("Analyse de la salle 306 (KB3) avec inventaire automatique des objets visibles.")

# --- INITIALISATION CLIENT GEMINI ---
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("⚠️ Clé API Gemini manquante. Veuillez configurer le fichier `.streamlit/secrets.toml`.")
    st.stop()

# --- 1. SÉLECTION ET CAPTURE DE L'IMAGE ---
methode = st.radio(
    "Comment souhaitez-vous ajouter votre photo ?",
    ("Prendre une photo en direct", "Sélectionner une photo depuis l'appareil")
)

image_source = None

if methode == "Prendre une photo en direct":
    picture = st.camera_input("Prendre une photo")
    if picture:
        image_source = picture
else:
    uploaded_file = st.file_uploader("Choisissez une image...", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        image_source = uploaded_file

st.divider()

# --- 2. ANALYSE PAR GEMINI ---
if image_source is not None:
    img = Image.open(image_source)
    
    st.button("🔄 Relancer l'analyse")
    
    with st.spinner("🧠 Gemini analyse la salle et dresse l'inventaire des objets..."):
        try:
            # Mise à jour du prompt pour demander le catalogue d'objets
            prompt = """
            Tu es un inspecteur de sécurité et un gestionnaire d'inventaire pour la salle 306 du bâtiment KB3.
            Analyse la photo et effectue deux tâches :
            
            1. SÉCURITÉ : Vérifie les règles (Max 9 personnes, max 8 étudiants, chaises bien positionnées, TV allumée, fenêtres fermées).
            2. INVENTAIRE : Identifie TOUS les objets importants visibles sur la photo (ex: Table, Chaise, Télévision, Fenêtre, Ordinateur, Sac à dos, Tableau blanc, etc.). 
               Pour chaque type d'objet unique trouvé, donne son utilisation/rôle standard dans cette salle de classe.

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
            Si aucun incident, "incidents" doit être []. Si aucun objet, "catalogue_objets" doit être [].
            """
            
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[img, prompt]
                )
            except Exception as e:
                if "503" in str(e):
                    st.warning("⚠️ Modèle principal surchargé, bascule sur le modèle de secours...")
                    response = client.models.generate_content(
                        model='gemini-2.0-flash', 
                        contents=[img, prompt]
                    )
                else:
                    raise e
            
            texte_reponse = response.text.strip()
            if texte_reponse.startswith("```json"):
                texte_reponse = texte_reponse.split("```json")[1].split("```")[0].strip()
                
            resultat = json.loads(texte_reponse)
            
        except Exception as e:
            st.error(f"❌ Erreur lors de l'analyse : {e}")
            st.stop()

    st.success("✅ Analyse et inventaire terminés !")
    
    # --- 3. AFFICHAGE DES INCIDENTS ---
    st.subheader("📊 Rapport de Conformité")
    st.metric(label="Personnes détectées", value=resultat["nb_personnes"])
    
    liste_incidents = resultat["incidents"]
    if not liste_incidents:
        st.success(f"✅ **Salle conforme :** {resultat['diagnostic_general']}")
    else:
        for inc in liste_incidents:
            if inc["gravite"] == "Critique":
                st.error(f"**[{inc['type']}]** : {inc['description']}")
            else:
                st.warning(f"**[{inc['type']}]** : {inc['description']}")
                
    st.divider()
    
    # --- 4. AFFICHAGE DU CATALOGUE DE DONNÉES (Nouveauté) ---
    st.subheader("📋 Catalogue des Données et Objets Visibles")
    st.write("Voici la liste des équipements détectés par l'IA et leur fonction dans la pièce :")
    
    liste_objets = resultat.get("catalogue_objets", [])
    
    if liste_objets:
        # On convertit la liste JSON en un tableau propre grâce à Streamlit et la structure native Python
        st.dataframe(
            liste_objets,
            column_config={
                "objet": "Équipement / Objet",
                "quantite_visible": "Quantité détectée",
                "utilisation": "Utilisation / Rôle dans la salle 306"
            },
            hide_index=True,
            width="stretch"
        )
    else:
        st.info("Aucun objet spécifique n'a pu être répertorié sur cette photo.")

    st.divider()
    
    # Vue de la photo originale
    st.subheader("🖼️ Cliché inspecté")
    st.image(img, caption="Image analysée par Gemini Vision", width="stretch")