import requests
import json
import os
import time
import urllib.parse
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
    """Récupère les dates de sortie à venir sur IGDB pour les plateformes majeures."""
    url = "https://api.igdb.com/v4/release_dates"
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    current_timestamp = int(time.time())
    
    # REQUÊTE SIMPLIFIÉE : On demande à IGDB d'inclure la catégorie, 
    # mais on enlève le filtre complexe d'ici pour éviter qu'il ne plante.
    query = f"""
    fields game.name, game.cover.image_id, date, platform.name, game.category;
    where date > {current_timestamp} & platform = (6,130,167,169);
    sort date asc;
    limit 500;
    """
    
    response = requests.post(url, headers=headers, data=query)
    response.raise_for_status()
    return response.json()

def format_games_data(raw_data):
    """Nettoie les données brutes et prépare le JSON pour notre interface Web."""
    formatted_games = []
    
    for item in raw_data:
        if 'game' not in item or 'name' not in item['game']:
            continue
            
        game_info = item['game']
        
        # NOUVEAU : Le filtrage se fait ici, en local, par notre script Python.
        # On vérifie la catégorie (0=Main Game, 8=Remake, 9=Remaster). 
        # Si c'est un DLC ou autre chose, on l'ignore (continue).
        categorie_jeu = game_info.get('category', 0)
        if categorie_jeu not in [0, 8, 9]:
            continue
        
        # 1. Formatage de la date
        try:
            date_obj = datetime.fromtimestamp(item['date'])
            formatted_date = date_obj.strftime('%d/%m/%Y')
        except KeyError:
            continue

        # 2. Récupération de la jaquette sécurisée
        cover_url = ""
        if 'cover' in game_info and 'image_id' in game_info['cover']:
            cover_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{game_info['cover']['image_id']}.jpg"
        else:
            # Encodage sécurisé pour éviter les crashs avec des symboles comme ":"
            texte_url = urllib.parse.quote(game_info['name'])
            cover_url = f"https://placehold.co/600x800/1e1e1e/00ffcc?text={texte_url}"
            
        # 3. Simplification des noms de plateformes
        platform_name = "Autre"
        if 'platform' in item and 'name' in item['platform']:
            p_name = item['platform']['name']
            if "PlayStation" in p_name:
                platform_name = "PlayStation"
            elif "Xbox" in p_name:
                platform_name = "Xbox"
            elif "Nintendo" in p_name or "Switch" in p_name:
                platform_name = "Nintendo"
            elif "PC" in p_name:
                platform_name = "PC"
            else:
                platform_name = p_name

        formatted_games.append({
            "titre": game_info['name'],
            "date": formatted_date,
            "timestamp": item['date'],
            "plateforme": platform_name,
            "jaquette": cover_url
        })
        
    # 4. Suppression des doublons
    unique_games = []
    seen = set()
    for g in formatted_games:
        identifier = f"{g['titre']}_{g['plateforme']}"
        if identifier not in seen:
            seen.add(identifier)
            unique_games.append(g)
            
    return unique_games

if __name__ == '__main__':
    print("Démarrage du Projet P - Extraction des données...")
    try:
        token = get_twitch_access_token(CLIENT_ID, CLIENT_SECRET)
        raw_data = fetch_upcoming_games(CLIENT_ID, token)
        
        clean_data = format_games_data(raw_data)
        print(f"✅ SUCCÈS : {len(clean_data)} jeux uniques trouvés (sur {len(raw_data)} dates brutes) !")
        
        with open('sorties.json', 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=4)
            
        print("Rechargez votre page web (Ctrl+F5) pour voir les nouveautés.")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution : {e}")