import pandas as pd
import matplotlib.pyplot as plt
import os
from storage import load_existing_activities, graph_dir # graph_dir est importé


def prepare_data(activities):
    """
    Charge les activités dans un DataFrame, convertit les unités (mètres/secondes -> km/heures)
    et prépare la colonne de l'année pour l'analyse.
    """
    if not activities:
        print("Erreur : La liste d'activités est vide.")
        return pd.DataFrame()

    df = pd.DataFrame(activities)

    # 1. Conversion de la date et extraction de l'année
    df['start_date'] = pd.to_datetime(df['start_date']).dt.tz_localize(None)
    df['year'] = df['start_date'].dt.year

    # 2. Conversion des unités pour la visualisation
    df['distance_km'] = df['distance'] / 1000
    df['moving_time_hours'] = df['moving_time'] / 3600
    df['elapsed_time_hours'] = df['elapsed_time'] / 3600

    return df

def aggregate_yearly_data(df):
    """
    Regroupe les données par année et calcule les sommes totales.
    """
    if df.empty:
        return pd.DataFrame()

    df_yearly = df.groupby('year').agg(
        total_distance_km=('distance_km', 'sum'),
        total_elevation_gain=('total_elevation_gain', 'sum'),
        total_moving_time_hours=('moving_time_hours', 'sum'),
        total_elapsed_time_hours=('elapsed_time_hours', 'sum'),
        activity_count=('id', 'count')
    ).reset_index()

    df_yearly['year'] = df_yearly['year'].astype(int)

    return df_yearly

def plot_yearly_evolution_separate(df_yearly, save_path=None):
    """
    Génère et sauvegarde un graphique individuel pour chaque métrique d'évolution annuelle.
    
    :param df_yearly: DataFrame des statistiques annuelles.
    :param athlete_id: ID de l'athlète pour nommer les fichiers.
    :param save_path: Chemin du répertoire où sauvegarder les graphiques.
    """
    if df_yearly.empty:
        print("Aucune donnée annuelle à afficher.")
        return

    plt.style.use('seaborn-v0_8-darkgrid')
    years = df_yearly['year'].astype(str) # Utiliser l'année en tant que chaîne pour l'axe X

    # Définition des métriques : (colonne, titre_du_graphique, label_Y, couleur, format_texte, préfixe_nom_fichier)
    metrics_to_plot = [
        ('total_distance_km', "Évolution Annuelle de la Distance (km)", "Distance (km)", 'tab:blue', "{:.0f} km", "distance_km"),
        ('total_elevation_gain', "Évolution Annuelle du Dénivelé Positif (D+)", "D+ (m)", 'tab:orange', "{:.0f} m", "denivele_positif"),
        ('total_moving_time_hours', "Évolution Annuelle du Temps de Mouvement (Heures)", "Heures", 'tab:green', "{:.0f} h", "temps_mouvement"),
        ('total_elapsed_time_hours', "Évolution Annuelle du Temps d'Activité Écoulé (Heures)", "Heures", 'tab:red', "{:.0f} h", "temps_ecoule"),
    ]

    for col, title, ylabel, color, format_str, file_prefix in metrics_to_plot:
        # Crée une NOUVELLE figure et un NOUVEL axe pour chaque graphique
        fig, ax = plt.subplots(figsize=(10, 6))
        values = df_yearly[col]

        # Diagramme à barres (historique)
        ax.bar(years, values, color=color, alpha=0.7)
        # Ligne de tendance (évolution)
        ax.plot(years, values, color='black', marker='o', linestyle='--', linewidth=1)

        ax.set_title(title, fontsize=14)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Année")

        # Ajout des étiquettes de valeur sur les barres
        for j, v in enumerate(values):
            y_position = v * 1.02
            ax.text(j, y_position, format_str.format(v), ha='center', fontsize=9) 

        ax.set_ylim(bottom=0) # Assurer que l'axe y commence à zéro
        plt.tight_layout() # Ajuste automatiquement l'espace pour que tout rentre

        # Crée un nom de fichier unique pour chaque graphique
        file_name = os.path.join(save_path, f"strava_evolution_{file_prefix}.png")
        plt.savefig(file_name, dpi=300, bbox_inches='tight')
        print(f"Graphique sauvegardé : {file_name}")
        plt.close(fig) # Ferme la figure pour libérer la mémoire après la sauvegarde


athlete_id = 18278258
activities = load_existing_activities(athlete_id)

df_activities = prepare_data(activities)

df_yearly_stats = aggregate_yearly_data(df_activities)

# Afficher un aperçu
if not df_yearly_stats.empty:
    print("--- SYNTHÈSE ANNUELLE ---")
    print(df_yearly_stats.to_string(index=False, float_format="%.1f"))
    print("-" * 40)
    
    plot_yearly_evolution_separate(df_yearly_stats, graph_dir(athlete_id))
else:
    print("Processus terminé : Aucune donnée à analyser après le chargement.")