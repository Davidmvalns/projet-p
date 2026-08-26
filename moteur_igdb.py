import requests
import json
import time
from datetime import datetime
import os
import sys

def get_twitch_access_token(client_id, client_secret):
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
    
    # 130 = Switch, 48 = PS4, 167 = PS5, 49 = XONE, 169 = XSX, 6 = PC
    platforms_config = [
        {"name": "PlayStation", "ids": "48,167"},
        {"name": "Xbox", "ids": "49,169"},
        {"name": "Nintendo", "ids": "130"},
        {"name": "PC", "ids": "6"}
    ]
    
    for plat in platforms_config:
        # NOUVELLE METHODE INFAILLIBLE : On cherche directement dans le calendrier, en exigeant un vrai jeu et une jaquette.
        query = f"""
        fields date, game.name, game.cover.image_id;
        where game.category = (0,8,9) 
        & game.cover != null 
        & platform = ({plat['ids']}) 
        & date > {current_timestamp};
        sort date asc;
        limit 150;
        """
        
        response = requests.post("https://api.igdb.com/v4/release_dates", headers=headers, data=query)
        response.raise_for_status()
        dates_data = response.json()
        
        for item in dates_data:
            if 'game' in item and 'name' in item['game'] and 'cover' in item['game']:
                all_games.append({
                    "titre": item['game']['name'],
                    "timestamp": item['date'],
                    "plateforme": plat['name'],
                    "jaquette_id": item['game']['cover']['image_id']
                })
                
    return all_games

def format_games_data(raw_data):
    formatted_games = []
    seen_combos = set()
    
    for item in raw_data:
        # On empêche un jeu d'apparaître 2 fois sur la même console (ex: version physique vs digitale)
        combo_id = f"{item['titre']}_{item['plateforme']}"
        if combo_id in seen_combos:
            continue
            
        seen_combos.add(combo_id)
        
        date_obj = datetime.fromtimestamp(item['timestamp'])
        formatted_date = date_obj.strftime('%d/%m/%Y')
        
        formatted_games.append({
            "titre": item['titre'],
            "date": formatted_date,
            "timestamp": item['timestamp'],
            "plateforme": item['plateforme'],
            "jaquette": f"https://images.igdb.com/igdb/image/upload/t_cover_big/{item['jaquette_id']}.jpg"
        })
        
    formatted_games = sorted(formatted_games, key=lambda x: x['timestamp'])
    return formatted_games

if __name__ == '__main__':
    try:
        # Récupération sécurisée
        CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
        CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
        
        if not CLIENT_ID or not CLIENT_SECRET:
            raise ValueError("Les clés Twitch sont introuvables. Vérifiez les secrets GitHub.")
            
        token = get_twitch_access_token(CLIENT_ID, CLIENT_SECRET)
        raw_data = fetch_all_platforms(CLIENT_ID, token)
        clean_data = format_games_data(raw_data)
        
        if len(clean_data) == 0:
            raise ValueError("Le script a fonctionné, mais l'API a renvoyé 0 jeux. Les filtres sont peut-être trop stricts.")
            
        with open('sorties.json', 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        # SI QUOI QUE CE SOIT PLANTE, LE SCRIPT L'ÉCRIT DANS LE JSON POUR VOUS L'AFFICHER !
        error_data = [{
            "titre": f"⚠️ ERREUR ROBOT PYTHON",
            "date": "Diagnostic",
            "timestamp": int(time.time()) + 86400,
            "plateforme": "PC",
            "jaquette": "",
            "message": str(e)
        }]
        with open('sorties.json', 'w', encoding='utf-8') as f:
            json.dump(error_data, f, ensure_ascii=False, indent=4)
        print(f"Erreur reportée : {e}")
