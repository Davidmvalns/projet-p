import requests
import json
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

def get_twitch_access_token(client_id, client_secret):
    """Récupère le jeton d'accès sécurisé via Twitch."""
    url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
    response = requests.post(url)
    response.raise_for_status()
    return response.json()['access_token']

def fetch_upcoming_games(client_id, access_token):
    """NOUVELLE MÉTHODE : Interroge la base des JEUX (et non plus des dates)."""
    # On cible directement les jeux pour éviter les doublons de dates par pays
    url = "https://api.igdb.com/v4/games"
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    current_timestamp = int(time.time())
    
    # REQUÊTE BLINDÉE :
    # category = (0,8,9) -> Uniquement Jeux principaux, Remakes, Remasters
    # cover != null -> Obligation d'avoir une jaquette
    # On récupère les 300 prochains vrais jeux !
    query = f"""
    fields name, cover.image_id, first_release_date, platforms.name;
    where first_release_date > {current_timestamp} 
    & platforms = (6,130,167,169,48,49) 
    & category = (0,8,9) 
    & cover != null;
    sort first_release_date asc;
    limit 300;
    """
    
    response = requests.post(url, headers=headers, data=query)
    response.raise_for_status()
    return response.json()

def format_games_data(raw_data):
    """Formate et trie les jeux par plateforme de manière stricte."""
    formatted_games = []
    
    for game in raw_data:
        if 'first_release_date' not in game or 'name' not in game:
            continue
            
        # 1. Formatage de la date de sortie initiale
        try:
            date_obj = datetime.fromtimestamp(game['first_release_date'])
            formatted_date = date_obj.strftime('%d/%m/%Y')
        except KeyError:
            continue

        # 2. Récupération de la vraie jaquette associée au jeu
        cover_url = ""
        if 'cover' in game and 'image_id' in game['cover']:
            cover_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{game['cover']['image_id']}.jpg"
            
        # 3. Répartition propre par plateforme
        is_playstation = False
        is_xbox = False
        is_nintendo = False
        is_pc = False
        
        if 'platforms' in game:
            for p in game['platforms']:
                p_name = p.get('name', '')
                if "PlayStation" in p_name: is_playstation = True
                if "Xbox" in p_name: is_xbox = True
                if "Nintendo" in p_name or "Switch" in p_name: is_nintendo = True
                if "PC" in p_name: is_pc = True
        
        # On crée une carte pour chaque plateforme sur laquelle le jeu sort
        platforms_to_add = []
        if is_playstation: platforms_to_add.append("PlayStation")
        if is_xbox: platforms_to_add.append("Xbox")
        if is_nintendo: platforms_to_add.append("Nintendo")
        if is_pc: platforms_to_add.append("PC")
            
        for plat in platforms_to_add:
            formatted_games.append({
                "titre": game['name'],
                "date": formatted_date,
                "timestamp": game['first_release_date'],
                "plateforme": plat,
                "jaquette": cover_url
            })
            
    return formatted_games

if __name__ == '__main__':
    print("Démarrage du Projet P - Moteur V3...")
    try:
        token = get_twitch_access_token(CLIENT_ID, CLIENT_SECRET)
        raw_data = fetch_upcoming_games(CLIENT_ID, token)
        
        clean_data = format_games_data(raw_data)
        print(f"✅ SUCCÈS : {len(clean_data)} fiches consoles créées (à partir de {len(raw_data)} vrais jeux uniques) !")
        
        with open('sorties.json', 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution : {e}")
