import streamlit as st
from PIL import Image
from google import genai
import json
import sqlite3
import streamlit_authenticator as stauth

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="S.A.M. - Salle 306", 
    page_icon="🛡️", 
    layout="wide"
)

# --- 2. FONCTIONS DE LA BASE DE DONNÉES SQLITE ---
def load_users_from_db():
    conn = sqlite3.connect("utilisateurs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, name, password FROM users")
    rows = cursor.fetchall()
    conn.close()
    credentials = {"usernames": {}}
    for row in rows:
        credentials["usernames"][row[0]] = {"name": row[1], "password": row[2]}
    return credentials

def save_analysis_to_history(username, statut, nb_personnes, result_json):
    """Sauvegarde le résultat d'un scan dans l'historique de l'utilisateur."""
    conn = sqlite3.connect("utilisateurs.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO history (username, statut, nb_personnes, json_complet)
        VALUES (?, ?, ?, ?)
    """, (username, statut, nb_personnes, json.dumps(result_json)))
    conn.commit()
    conn.close()

def load_user_history(username):
    """Récupère l'historique complet d'un utilisateur spécifique."""
    conn = sqlite3.connect("utilisateurs.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date_analyse, statut, nb_personnes, json_complet 
        FROM history 
        WHERE username = ? 
        ORDER BY date_analyse DESC
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return rows

try:
    credentials = load_users_from_db()
except sqlite3.OperationalError:
    st.error("❌ Base de données introuvable. Exécutez 'init_db.py' d'abord.")
    st.stop()

# --- 3. CONFIGURATION DE L'AUTHENTIFICATION & INSCRIPTION ---
authenticator = stauth.Authenticate(
    credentials,
    st.secrets["cookie"]["name"],
    st.secrets["cookie"]["key"],
    int(st.secrets["cookie"]["expiry_days"])
)

# Vérification du statut de connexion actuel (via cookies)
authentication_status = st.session_state.get("authentication_status")

if not authentication_status:
    # Interface avec deux onglets pour l'accès avant connexion
    tab_login, tab_register = st.tabs(["🔐 Se connecter", "📝 Nouvel utilisateur ?"])
    
    with tab_login:
        authenticator.login(location='main')
        authentication_status = st.session_state.get("authentication_status")
        
        if authentication_status is False:
            st.error("❌ Utilisateur ou mot de passe incorrect.")
            
    with tab_register:
        st.subheader("Créer un nouveau compte Professeur / Inspecteur")
        with st.form("inscription_form"):
            new_username = st.text_input("Nom d'utilisateur (Identifiant unique)")
            new_name = st.text_input("Nom complet (ex: Dr. Jean Dupont)")
            new_password = st.text_input("Mot de passe", type="password")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password")
            submit_reg = st.form_submit_button("Créer mon compte", use_container_width=True)
            
            if submit_reg:
                if not new_username or not new_name or not new_password:
                    st.error("⚠️ Veuillez remplir tous les champs.")
                elif new_password != confirm_password:
                    st.error("❌ Les mots de passe ne correspondent pas.")
                elif new_username in credentials["usernames"]:
                    st.error("❌ Cet identifiant est déjà utilisé par un autre utilisateur.")
                else:
                    try:
                        hashed_new_password = stauth.Hasher.hash_list([new_password])[0]
                        conn = sqlite3.connect("utilisateurs.db")
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (username, name, password) VALUES (?, ?, ?)", 
                                       (new_username.strip(), new_name.strip(), hashed_new_password))
                        conn.commit()
                        conn.close()
                        st.success("🎉 Compte créé ! Allez sur l'onglet 'Se connecter'.")
                        st.balloons()
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"Erreur lors de la création du compte : {e}")

# --- 4. SI ET SEULEMENT SI CONNECTÉ : RENDU DE L'APPLICATION ---
if st.session_state.get("authentication_status"):
    
    name = st.session_state.get("name")
    username = st.session_state.get("username")

    # Style CSS personnalisé
    st.html("""
        <style>
        .main-title {
            font-size: 2.8rem !important; font-weight: 800;
            background: linear-gradient(45deg, #FF4B4B, #FF8585);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .custom-card {
            border-radius: 10px; padding: 15px; background-color: #f0f2f6;
            margin-bottom: 10px; border-left: 5px solid #FF4B4B;
        }
        </style>
    """)

    # En-tête de l'interface
    st.html('<h1 class="main-title">🛡️ S.A.M. - Salle 306</h1>')
    st.caption(f"Bonjour **{name}** | Session active : `{username}`")

    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception:
        st.error("⚠️ Clé API Gemini manquante.")
        st.stop()

    # Architecture en colonnes du Tableau de Bord
    col_gauche, col_droite = st.columns([1, 2], gap="large")

    with col_gauche:
        st.subheader("🎛️ Panneau de Contrôle")
        
        # Le bouton de déconnexion est maintenant protégé à 100% par la condition IF
        authenticator.logout('🚪 Se déconnecter', 'main')
        st.divider()
        
        methode = st.pills("Mode d'acquisition :", ["Prendre une photo", "Importer un fichier"], selection_mode="single", default="Prendre une photo")
        
        image_source = None
        if methode == "Prendre une photo":
            image_source = st.camera_input("Déclencher la caméra")
        else:
            image_source = st.file_uploader("Fichier image (JPG/PNG)", type=["png", "jpg", "jpeg"])
            
        st.divider()
        st.markdown("🔍 **Incidents recherchés automatiquement :**")
        st.info("* 🚨 Surcharge | * 🪑 Manque de tables | * 👥 Mauvais placement\n* 🔕 TV éteinte | * 🪟 Fenêtre ouverte | * 🪵 Chaise renversée")

    with col_droite:
        tab_rapport, tab_catalogue, tab_image, tab_historique = st.tabs([
            "📋 Rapport d'Incidents", 
            "🗂️ Inventaire des Objets", 
            "🖼️ Image Source",
            "⏳ Mon Historique"
        ])
        
        if image_source is not None:
            img = Image.open(image_source)
            
            if "last_result" not in st.session_state or st.button("🔄 Forcer une ré-analyse", use_container_width=True):
                with st.spinner("🧠 S.A.M. analyse la salle..."):
                    try:
                        prompt = """
                        Tu es un inspecteur de sécurité pour la salle 306 du bâtiment KB3.
                        Analyse la photo et répond UNIQUEMENT sous forme d'un JSON strict :
                        {
                            "nb_personnes": <int>,
                            "incidents": [{"type": "<Nom>", "gravite": "<Critique/Avertissement>", "description": "<Texte>"}],
                            "diagnostic_general": "<Synthèse>",
                            "catalogue_objets": [{"objet": "<Nom>", "quantite_visible": "<Nbr>", "utilisation": "<Rôle>"}]
                        }
                        Les types d'incidents : "Surcharge", "Manque de tables", "Non-respect du placement", "Chaise renversée", "TV éteinte", "Fenêtre ouverte".
                        """
                        try:
                            response = client.models.generate_content(model='gemini-2.5-flash', contents=[img, prompt])
                        except Exception:
                            response = client.models.generate_content(model='gemini-2.0-flash', contents=[img, prompt])
                        
                        texte = response.text.strip().replace("```json", "").replace("```", "").strip()
                        resultat = json.loads(texte)
                        st.session_state["last_result"] = resultat
                        
                        statut_analyse = "Anomalie" if resultat.get("incidents") else "Conforme"
                        save_analysis_to_history(username, statut_analyse, resultat["nb_personnes"], resultat)
                        
                    except Exception as e:
                        st.error(f"❌ Erreur IA : {e}")
                        st.stop()
            
            resultat = st.session_state["last_result"]
            liste_incidents = resultat.get("incidents", [])
            
            with tab_rapport:
                st.subheader("📊 Métriques Actuelles")
                m1, m2, m3 = st.columns(3)
                m1.metric("Humains détectés", f"{resultat['nb_personnes']} / 9")
                m2.metric("Alertes actives", len(liste_incidents))
                m3.metric("Statut Pièce", "Conforme" if not liste_incidents else "Anomalie")
                st.divider()
                
                if not liste_incidents:
                    st.success(f"🌱 **Aucune anomalie détectée :** {resultat['diagnostic_general']}")
                else:
                    for inc in liste_incidents:
                        st.html(f"""
                        <div class="custom-card" style="border-left-color: {'#FF4B4B' if inc['gravite'] == 'Critique' else '#FFAA00'}">
                            <h4 style="margin-top:0; margin-bottom:5px;">🔴 {inc['type']} ({inc['gravite']})</h4>
                            <p style="margin:0; color:#333; font-size:0.95rem;">{inc['description']}</p>
                        </div>
                        """)
                    st.info(f"💡 **Note globale de synthèse :** {resultat['diagnostic_general']}")
            
            with tab_catalogue:
                st.dataframe(resultat.get("catalogue_objets", []), hide_index=True, use_container_width=True)
                
            with tab_image:
                st.image(img, use_container_width=True)
                
        else:
            with tab_rapport:
                st.info("📌 En attente d'une capture photo ou d'un fichier importé à gauche.")

        with tab_historique:
            st.subheader(f"⏳ Rapports de diagnostic de `{username}`")
            historique_data = load_user_history(username)
            
            if not historique_data:
                st.info("Vous n'avez effectué aucune analyse pour le moment.")
            else:
                affichage_historique = []
                for row in historique_data:
                    date_clean = row[0].split(".")[0]
                    icon_statut = "🟢 Conforme" if row[1] == "Conforme" else "🔴 Anomalie"
                    affichage_historique.append({
                        "Date & Heure": date_clean,
                        "Verdict": icon_statut,
                        "Personnes détectées": f"{row[2]} personnes"
                    })
                st.dataframe(affichage_historique, use_container_width=True, hide_index=True)
