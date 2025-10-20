# heatmap.py
# Génère un fichier GeoJSON LineString optimisé, centré sur une zone géographique donnée.

import glob
import gpxpy
import numpy as np
from tqdm import tqdm
from collections import defaultdict
import json
import os
from storage import gpx_dir, heatmap_geojson_path

# ==================================================================================
# PARAMÈTRES ET OUTILS (Inchangés)
# ==================================================================================

CENTER_LAT = 43.60  
CENTER_LON = 3.88   
EXTENT_KM = 25      
DENSITY_PRECISION_DECIMALS = 4 
MIN_SEGMENT_LENGTH_M = 5 

# ... (Fonctions calculate_bounding_box, heatmap_geojson_path, get_density_value, get_color_hex inchangées) ...

def calculate_bounding_box(center_lat, center_lon, extent_km):
    """Calcule la Bounding Box (Lat/Lon min/max)."""
    LAT_KM_PER_DEG = 111.32 
    LON_KM_PER_DEG = 111.32 * np.cos(np.radians(center_lat))
    lat_delta_deg = extent_km / LAT_KM_PER_DEG
    lon_delta_deg = extent_km / LON_KM_PER_DEG
    
    lat_min = center_lat - lat_delta_deg
    lat_max = center_lat + lat_delta_deg
    lon_min = center_lon - lon_delta_deg
    lon_max = center_lon + lon_delta_deg
    return lat_min, lat_max, lon_min, lon_max

def get_density_value(count, log_min, log_range):
    if log_range == 0: return 1.0
    log_count = np.log10(count)
    return (log_count - log_min) / log_range

def get_color_hex(value):
    value = np.clip(value, 0, 1) 
    r = int(255 * value)
    g = int(255 * value)
    b = int(255 * (1 - value)) 
    return '#{0:02x}{1:02x}{2:02x}'.format(r, g, b)


# ==================================================================================
# 2. AGRÉGATION ET FILTRAGE (Inchangée)
# ==================================================================================

# Calcul des bornes globales
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = calculate_bounding_box(CENTER_LAT, CENTER_LON, EXTENT_KM)

def aggregate_segment_density(gpx_base_dir):
    """
    Collecte, filtre géographiquement (en utilisant les bornes globales) 
    et compte la densité des segments (4 décimales).
    """
    segment_counts = defaultdict(int)
    # ... (Logique de lecture GPX, filtre, arrondi et comptage inchangée) ...
    for path in tqdm(glob.glob(f"{gpx_base_dir}/**/*.gpx", recursive=True), desc="Comptage et Filtrage"):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)
            
            for track in gpx.tracks:
                for segment in track.segments:
                    for i in range(len(segment.points) - 1):
                        p1, p2 = segment.points[i], segment.points[i+1]

                        # FILTRAGE GÉOGRAPHIQUE
                        is_p1_in = (LAT_MIN <= p1.latitude <= LAT_MAX and LON_MIN <= p1.longitude <= LON_MAX)
                        is_p2_in = (LAT_MIN <= p2.latitude <= LAT_MAX and LON_MIN <= p2.longitude <= LON_MAX)
                        if not (is_p1_in or is_p2_in): continue 
                        
                        # Arrondi (4 décimales) et Clé unique
                        coords_a = (round(p1.latitude, DENSITY_PRECISION_DECIMALS), round(p1.longitude, DENSITY_PRECISION_DECIMALS))
                        coords_b = (round(p2.latitude, DENSITY_PRECISION_DECIMALS), round(p2.longitude, DENSITY_PRECISION_DECIMALS))
                        key = tuple(sorted((coords_a, coords_b)))
                        
                        if p1.distance_3d(p2) is not None and p1.distance_3d(p2) < MIN_SEGMENT_LENGTH_M: continue

                        segment_counts[key] += 1
                        
        except Exception:
            pass

    # Regroupement par DENSITÉ (pour l'optimisation MultiLineString)
    segments_by_count = defaultdict(list)
    for segment_key, count in segment_counts.items():
        segments_by_count[count].append(segment_key)
        
    print(f"\nSegments uniques (après simplification et filtre) : {len(segment_counts)}")
    print(f"Niveaux de densité (Features GeoJSON) : {len(segments_by_count)}")
    return segments_by_count

# ==================================================================================
# 3. GÉNÉRATION GEOJSON OPTIMISÉ (CORRIGÉ POUR L'INDENTATION FIABLE)
# ==================================================================================

def generate_density_geojson_optimized(segments_by_count, output_path):
    """
    Génère le GeoJSON optimisé avec MultiLineString, BBox, et l'indentation.
    """
    if not segments_by_count: return

    # Calcul de l'échelle de couleur 
    all_counts = np.array(list(segments_by_count.keys()))
    min_count, max_count = all_counts.min(), all_counts.max()
    log_min, log_max = np.log10(min_count), np.log10(max_count)
    log_range = log_max - log_min

    features = []
    
    for count, segment_keys in tqdm(segments_by_count.items(), desc="Génération GeoJSON"):
        density_value = get_density_value(count, log_min, log_range)
        color = get_color_hex(density_value)
        
        multiline_coords = []
        for coords_a, coords_b in segment_keys:
            multiline_coords.append([[coords_a[1], coords_a[0]], [coords_b[1], coords_b[0]]])

        # Création de la Feature (structuration plus verbeuse pour la fiabilité)
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "MultiLineString", 
                "coordinates": multiline_coords
            },
            "properties": {
                "stroke": color, 
                "stroke-width": 2, 
                "stroke-opacity": 0.8, 
                "density_count": count
            }
        }
        features.append(feature)

    # Structure GeoJSON finale
    geojson_output = {
        "type": "FeatureCollection", 
        "features": features,
        "bbox": [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX] 
    }
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            # LIGNE CRUCIALE : Uniquement l'indentation
            json.dump(geojson_output, f, indent=2) 
            
        print(f"\nFichier GeoJSON sauvegardé : {output_path}")
    except Exception as e:
        print(f"ERREUR LORS DE LA CRÉATION DU GEOJSON : {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
            print("Fichier corrompu supprimé.")


# ==================================================================================
# 4. BLOC D'EXÉCUTION
# ==================================================================================

if __name__ == "__main__":
    
    athlete_id = 18278258 # REMPLACEZ PAR VOTRE ID D'ATHLÈTE
    
    print(f"--- Démarrage de la génération GeoJSON centrée pour l'athlète ID: {athlete_id} ---")

    gpx_base_dir = gpx_dir(athlete_id) 
    geojson_path = heatmap_geojson_path(athlete_id)

    # 1. Agrégation et regroupement par densité
    segments_by_count = aggregate_segment_density(gpx_base_dir)

    # 2. Génération du GeoJSON optimisé
    if segments_by_count:
        generate_density_geojson_optimized(segments_by_count, geojson_path)
    else:
        print("Aucun segment trouvé. Vérifiez le répertoire GPX et les chemins.")