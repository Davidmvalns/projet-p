import requests
import json
import time
from datetime import datetime
import os
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
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    current_timestamp = int(time.time())
    all_games = []
    
    platforms_config = [
        {"name": "PlayStation", "ids": "48,167"},
        {"name": "Xbox", "ids": "49,169"},
        {"name": "Nintendo", "ids": "130"},
        {"name": "PC", "ids": "6"}
    ]
    
    for plat in platforms_config:
        # NOUVEAUTÉ : On attaque la base "games" principale. Cela garantit la vraie jaquette et élimine les éditions bizarres.
        query = f"""
        fields name, cover.image_id, release_dates.date, release_dates.platform;
        where category = (0,8,9) 
        & cover != null 
        & platforms = ({plat['ids']})
        & release_dates.date > {current_timestamp};
        sort release_dates.date asc;
        limit 150;
        """
        
        try:
            response = requests.post("https://api.igdb.com/v4/games", headers=headers, data=query)
            response.raise_for_status()
            games_data = response.json()
            
            # On étiquette les jeux pour la plateforme cible
            for game in games_data:
                game['master_platform'] = plat['name']
                game['target_plat_ids'] = plat['ids']
            
            all_games.extend(games_data)
        except Exception as e:
            print(f"Erreur plateforme {plat['name']} : {e}")
            
    return all_games

def format_games_data(raw_data):
    formatted_games = []
    seen_names = set()
    current_timestamp = int(time.time())
    
    for game in raw_data:
        game_name = game.get('name', 'Inconnu')
        platform_family = game['master_platform']
        
        # 1 jeu = 1 seule apparition par console
        combo_id = f"{game_name}_{platform_family}"
        if combo_id in seen_names:
            continue
            
        if 'cover' not in game or 'image_id' not in game['cover']:
            continue
            
        cover_url = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{game['cover']['image_id']}.jpg"
        
        # Trouver la meilleure date parmi toutes les régions pour cette console
        best_date = None
        target_ids = [int(x) for x in game['target_plat_ids'].split(',')]
        
        for rd in game.get('release_dates', []):
            rd_date = rd.get('date')
            rd_plat = rd.get('platform')
            
            if rd_date and rd_plat in target_ids and rd_date > current_timestamp:
                if best_date is None or rd_date < best_date:
                    best_date = rd_date
                    
        if not best_date:
            continue
            
        seen_names.add(combo_id)
        
        # Formatage de la date
        date_obj = datetime.fromtimestamp(best_date)
        formatted_date = date_obj.strftime('%d/%m/%Y')
        
        formatted_games.append({
            "titre": game_name,
            "date": formatted_date,
            "timestamp": best_date,
            "plateforme": platform_family,
            "jaquette": cover_url
        })
        
    formatted_games = sorted(formatted_games, key=lambda x: x['timestamp'])
    return formatted_games

if __name__ == '__main__':
    print("Démarrage du Projet P - Extraction V4 (Jeux Officiels)...")
    try:
        token = get_twitch_access_token(CLIENT_ID, CLIENT_SECRET)
        raw_data = fetch_all_platforms(CLIENT_ID, token)
        clean_data = format_games_data(raw_data)
        
        with open('sorties.json', 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ SUCCÈS : {len(clean_data)} vrais jeux récupérés avec succès !")
    except Exception as e:
        print(f"❌ Erreur critique : {e}")
