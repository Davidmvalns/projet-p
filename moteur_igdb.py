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

def fetch_all_platforms(client_id, access_token):
    """Fait 4 recherches séparées pour garantir l'équilibre des consoles."""
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    current_timestamp = int(time.time())
    all_games = []
    
    # ID des consoles IGDB : PS (48,167), Xbox (49,169), Nintendo (130), PC (6)
    platforms_config = [
        {"name": "PlayStation", "ids": "48,167"},
        {"name": "Xbox", "ids": "49,169"},
        {"name": "Nintendo", "ids": "130"},
        {"name": "PC", "ids": "6"}
    ]
    
    for plat in platforms_config:
        # Requête très stricte : Uniquement jeux principaux (0,8,9), avec jaquette (!= null)
        query = f"""
        fields game.name, game.cover.image_id, date, platform.name;
        where date > {current_timestamp} 
        & platform = ({plat['ids']}) 
        & game.category = (0,8,9) 
        & game.cover != null;
        sort date asc;
        limit 150;
        """
        
        try:
            response = requests.post("https://api.igdb.com/v4/release_dates", headers=headers, data=query)
            response.raise_for_status()
            data = response.json()
            
            # On étiquette manuellement la famille de console
            for item in data:
                item['master_platform'] = plat['name']
            
            all_games.extend(data)
        except Exception as e:
            print(f"Erreur sur la plateforme {plat['name']} : {e}")
            
    return all_games

def format_games_data(raw_data):
    """Nettoie les données et élimine les doublons de dates."""
    formatted_games = []
    seen_combinations = set()
    
    for item in raw_data:
        # Sécurité : on vérifie que l'API a bien renvoyé toutes les infos
        if 'game' not in item or 'date' not in item or 'master_platform' not in item:
            continue
            
        game_data = item['game']
        game_name = game_data.get('name', 'Inconnu')
        platform_family = item['master_platform']
        
        # 1. Filtre Anti-Doublons (ex: si le jeu a 3 dates, on ne garde que la 1ère)
        combo_id = f"{game_name}_{platform_family}"
        if combo_id in seen_combinations:
            continue
        seen_combinations.add(combo_id)

        # 2. Sécurisation absolue de la jaquette
        if 'cover' in game_data and 'image_id' in game_data['cover']:
            cover_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{game_data['cover']['image_id']}.jpg"
        else:
            continue # S'il n'y a toujours pas d'image, on rejette purement le jeu

        # 3. Calcul de la date
        try:
            date_obj = datetime.fromtimestamp(item['date'])
            formatted_date = date_obj.strftime('%d/%m/%Y')
        except Exception:
            continue

        formatted_games.append({
            "titre": game_name,
            "date": formatted_date,
            "timestamp": item['date'],
            "plateforme": platform_family,
            "jaquette": cover_url
        })
        
    # On mélange toutes les consoles et on trie par date de sortie globale
    formatted_games = sorted(formatted_games, key=lambda x: x['timestamp'])
    return formatted_games

if __name__ == '__main__':
    print("Démarrage du Projet P - Moteur Ultime (Multi-Requêtes)...")
    try:
        token = get_twitch_access_token(CLIENT_ID, CLIENT_SECRET)
        raw_data = fetch_all_platforms(CLIENT_ID, token)
        clean_data = format_games_data(raw_data)
        
        with open('sorties.json', 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ SUCCÈS : {len(clean_data)} jeux parfaitement uniques et ciblés générés !")
    except Exception as e:
        print(f"❌ Erreur critique : {e}")
