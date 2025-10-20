import json
from datetime import datetime, timedelta
from datetime import datetime, timedelta, timezone
from xml.dom import minidom
import xml.etree.ElementTree as ET
from pathlib import Path
from storage import load_existing_activities, load_stream, gpx_path


def strava_stream_to_gpx(activity, athlete_id, output_dir="data/gpx"):
    """
    Convertit un fichier JSON Strava stream en fichier GPX
    
    Args:
        activity: Dictionnaire contenant les informations de l'activité
        user_id: ID de l'utilisateur Strava
        output_dir: Répertoire de sortie pour les fichiers GPX
    """
    
    # Construire le chemin du fichier JSON

    activity_id = activity['id']
    output_gpx = gpx_path(athlete_id, activity_id)
    if output_gpx.exists():
        print(f"→ Déjà converti: {output_gpx}")
        return True

    data = load_stream(athlete_id, activity_id)
    
    # Récupérer les informations de l'activité
    activity_name = activity.get('name', 'Strava Activity')
    sport_type = activity.get('sport_type', "unknown")
    start_date_str = activity.get('start_date', None)
    
    # Parser la date de début
    if start_date_str:
        # Format: "2025-10-19 06:35:22+00:00"
        start_time = datetime.fromisoformat(start_date_str.replace('+00:00', '+00:00'))
    else:
        start_time = datetime.now(timezone.utc)

    gpx = ET.Element('gpx', {
        'version': '1.1',
        'creator': 'Strava Stream Converter',
        'xmlns': 'http://www.topografix.com/GPX/1/1',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xmlns:gpxtpx': 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1',
        'xsi:schemaLocation': 'http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd'
    })
    
    # Métadonnées
    metadata = ET.SubElement(gpx, 'metadata')
    ET.SubElement(metadata, 'name').text = activity_name
    ET.SubElement(metadata, 'time').text = start_time.isoformat()
    
    # Description avec toutes les données de l'activité
    desc_parts = []
    desc_parts.append(f"Sport: {sport_type}")
    desc_parts.append(f"Distance: {activity.get('distance', 0):.2f} m")
    desc_parts.append(f"Temps en mouvement: {activity.get('moving_time', 0)} s")
    desc_parts.append(f"Temps écoulé: {activity.get('elapsed_time', 0)} s")
    desc_parts.append(f"Dénivelé positif: {activity.get('total_elevation_gain', 0)} m")
    desc_parts.append(f"Privé: {'Oui' if activity.get('private', False) else 'Non'}")
    ET.SubElement(metadata, 'desc').text = " | ".join(desc_parts)
    
    # Track
    trk = ET.SubElement(gpx, 'trk')
    ET.SubElement(trk, 'name').text = activity_name
    ET.SubElement(trk, 'type').text = sport_type
    
    # Track segment
    trkseg = ET.SubElement(trk, 'trkseg')

    if 'latlng' in data:

        # Créer les points de trace
        for i in range(len(data['latlng'])):
            lat, lon = data['latlng'][i]
            
            # Créer le trackpoint
            trkpt = ET.SubElement(trkseg, 'trkpt', {
                'lat': str(lat),
                'lon': str(lon)
            })
            
            # Altitude
            if i < len(data['altitude']):
                ET.SubElement(trkpt, 'ele').text = str(data['altitude'][i])
            
            # Temps (basé sur le timestamp)
            if i < len(data['time']):
                point_time = start_time + timedelta(seconds=data['time'][i])
                ET.SubElement(trkpt, 'time').text = point_time.isoformat() + 'Z'
            
            # Extensions Garmin pour données supplémentaires
            extensions = ET.SubElement(trkpt, 'extensions')
            gpxtpx_ext = ET.SubElement(extensions, 'gpxtpx:TrackPointExtension')


            # Température
            if 'temp' in data and i < len(data['temp']):
                ET.SubElement(gpxtpx_ext, 'gpxtpx:atemp').text = str(data['temp'][i])
            
            # Extensions personnalisées pour données Strava
            strava_ext = ET.SubElement(extensions, 'strava:data', {
                'xmlns:strava': 'http://www.strava.com/xmlschemas/v1'
            })
            
            # Vitesse lissée
            if 'velocity_smooth' in data and i < len(data['velocity_smooth']):
                ET.SubElement(strava_ext, 'strava:velocity_smooth').text = str(data['velocity_smooth'][i])
            
            # Pente lissée
            if 'grade_smooth' in data and i < len(data['grade_smooth']):
                ET.SubElement(strava_ext, 'strava:grade_smooth').text = str(data['grade_smooth'][i])
            
            # Distance cumulée
            if 'distance' in data and i < len(data['distance']):
                ET.SubElement(strava_ext, 'strava:distance').text = str(data['distance'][i])
            
            # En mouvement
            if 'moving' in data and i < len(data['moving']):
                ET.SubElement(strava_ext, 'strava:moving').text = str(data['moving'][i]).lower()

    else:
        output_gpx = output_gpx.with_name(output_gpx.stem + "_no_position.gpx")

    # Formater le XML avec indentation
    xml_str = minidom.parseString(ET.tostring(gpx)).toprettyxml(indent="  ")
    
    # Écrire dans le fichier
    with open(output_gpx, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    
    print(f"✓ {activity_name} ({activity_id})")
    return True


def convert_all_activities(activities, user_id):
    """
    Convertit toutes les activités Strava en fichiers GPX
    
    Args:
        activities: Liste des activités (dictionnaires)
        user_id: ID de l'utilisateur Strava
        output_dir: Répertoire de sortie pour les fichiers GPX
    """
    
    print(f"Conversion de {len(activities)} activités...\n")
    
    success_count = 0
    failed_count = 0
    
    for activity in activities:
        if strava_stream_to_gpx(activity, user_id):
            success_count += 1
        else:
            failed_count += 1
        # break
    
    print(f"\n{'='*50}")
    print(f"Conversion terminée :")
    print(f"  ✓ Réussies : {success_count}")
    print(f"  ✗ Échouées : {failed_count}")


# Exemple d'utilisation
if __name__ == "__main__":

    athlete_id = 18278258
    activities = load_existing_activities(athlete_id)
    convert_all_activities(activities, athlete_id)