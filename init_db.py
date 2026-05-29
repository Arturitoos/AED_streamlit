import sqlite3
import streamlit_authenticator as stauth

def initialiser_base():
    # 1. Connexion (crée le fichier s'il n'existe pas)
    conn = sqlite3.connect("utilisateurs.db")
    cursor = conn.cursor()

    # 2. Création de la table des utilisateurs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        name TEXT,
        password TEXT
    )
    """)

    # 3. Création de la table historique
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        date_analyse TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        statut TEXT,
        nb_personnes INTEGER,
        json_complet TEXT,
        FOREIGN KEY(username) REFERENCES users(username)
    )
    """)

    # 4. Génération du mot de passe administrateur par défaut (Epita2026)
    # Syntaxe officielle de classe pour les versions actuelles
    hashed_password = stauth.Hasher.hash_list(['Epita2026'])[0]

    # 5. Insertion du premier utilisateur admin (Ignoré s'il existe déjà)
    cursor.execute("""
    INSERT OR IGNORE INTO users (username, name, password) 
    VALUES (?, ?, ?)
    """, ("admin", "Administrateur Système", hashed_password))

    conn.commit()
    conn.close()
    print("✅ Base de données 'utilisateurs.db' initialisée avec succès !")

if __name__ == "__main__":
    initialiser_base()
