import pandas as pd
import matplotlib.pyplot as plt
import os
import calendar
import seaborn as sns 

from storage import load_existing_activities, graph_dir 

# ----------------------------------------------------------------------------------
# 1. FONCTIONS DE PRÉPARATION ET AGRÉGATION
# ----------------------------------------------------------------------------------

def prepare_data(activities):
    """
    Charge les activités dans un DataFrame, convertit les unités et prépare les colonnes de date.
    (CORRIGÉ : Assure que 'elapsed_time_hours' est créé)
    """
    if not activities:
        print("Erreur : La liste d'activités est vide.")
        return pd.DataFrame()

    df = pd.DataFrame(activities)

    # 1. Conversion de la date et extraction des colonnes pour l'analyse
    df['start_date'] = pd.to_datetime(df['start_date']).dt.tz_localize(None)
    df['year'] = df['start_date'].dt.year
    df['month'] = df['start_date'].dt.month
    df['day_of_week'] = df['start_date'].dt.dayofweek # 0=Lundi, 6=Dimanche

    # 2. Conversion des unités
    df['distance_km'] = df['distance'] / 1000
    df['moving_time_hours'] = df['moving_time'] / 3600
    df['elapsed_time_hours'] = df['elapsed_time'] / 3600 # LIGNE CLÉ RÉTABLIE
    
    # 3. Calcul de la vitesse moyenne
    df['avg_speed_kph'] = df['distance_km'] / df['moving_time_hours']
    
    # 4. Nettoyage
    df.replace([float('inf'), -float('inf')], float('nan'), inplace=True)
    df.dropna(subset=['avg_speed_kph'], inplace=True)
    
    return df

def aggregate_yearly_data(df):
    """
    Regroupe les données par année, calcule les sommes totales et arrondit les temps.
    """
    if df.empty:
        return pd.DataFrame()

    df_yearly = df.groupby('year').agg(
        total_distance_km=('distance_km', 'sum'),
        total_elevation_gain=('total_elevation_gain', 'sum'),
        total_moving_time_hours=('moving_time_hours', 'sum'),
        total_elapsed_time_hours=('elapsed_time_hours', 'sum'), # Cette colonne existe maintenant
        activity_count=('distance_km', 'count')
    ).reset_index()

    # Arrondir et convertir en entier pour les heures
    for col in ['total_moving_time_hours', 'total_elapsed_time_hours']:
        df_yearly.loc[:, col] = df_yearly[col].round(0).astype(int)

    df_yearly['year'] = df_yearly['year'].astype(int)
    return df_yearly

# ----------------------------------------------------------------------------------
# 2. FONCTIONS DE TRACÉ EXISTANTES (InchAngées)
# ----------------------------------------------------------------------------------

def plot_yearly_evolution_separate(df_yearly, save_path):
    if df_yearly.empty:
        print("Aucune donnée annuelle à afficher.")
        return
    plt.style.use('seaborn-v0_8-darkgrid')
    years = df_yearly['year'].astype(str) 
    metrics_to_plot = [
        ('total_distance_km', "Évolution Annuelle de la Distance (km)", "Distance (km)", 'tab:blue', "{:.0f} km", "distance_km"),
        ('total_elevation_gain', "Évolution Annuelle du Dénivelé Positif (D+)", "D+ (m)", 'tab:orange', "{:.0f} m", "denivele_positif"),
        ('total_moving_time_hours', "Évolution Annuelle du Temps de Mouvement (Heures)", "Heures", 'tab:green', "{:.0f} h", "temps_mouvement"),
        ('total_elapsed_time_hours', "Évolution Annuelle du Temps d'Activité Écoulé (Heures)", "Heures", 'tab:red', "{:.0f} h", "temps_ecoule"),
    ]
    for col, title, ylabel, color, format_str, file_prefix in metrics_to_plot:
        fig, ax = plt.subplots(figsize=(10, 6))
        values = df_yearly[col]
        ax.bar(years, values, color=color, alpha=0.7)
        ax.plot(years, values, color='black', marker='o', linestyle='--', linewidth=1)
        ax.set_title(title, fontsize=14)
        ax.set_ylabel(ylabel)
        ax.set_xlabel("Année")
        for j, v in enumerate(values):
            y_position = v * 1.02
            ax.text(j, y_position, format_str.format(v), ha='center', fontsize=9) 
        ax.set_ylim(bottom=0)
        plt.tight_layout() 
        file_name = os.path.join(save_path, f"strava_evolution_{file_prefix}.png")
        plt.savefig(file_name, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"Graphique sauvegardé : {file_name}")

# ----------------------------------------------------------------------------------
# 3. NOUVELLES FONCTIONS : Performance Moyenne Annuelle par Sport (InchAngées)
# ----------------------------------------------------------------------------------

def aggregate_avg_performance_by_sport(df):
    if df.empty: return pd.DataFrame()
    df_avg_speed = df.groupby(['year', 'sport_type']).agg(
        avg_speed_kph=('avg_speed_kph', 'mean')
    ).reset_index()
    df_avg_speed['year'] = df_avg_speed['year'].astype(int)
    return df_avg_speed

def plot_avg_speed_per_sport_yearly(df_avg_speed, save_path):
    if df_avg_speed.empty:
        print("Aucune donnée de performance annuelle à afficher.")
        return
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(12, 7))
    for sport in df_avg_speed['sport_type'].unique():
        df_sport = df_avg_speed[df_avg_speed['sport_type'] == sport]
        ax.plot(df_sport['year'], df_sport['avg_speed_kph'], marker='o', linestyle='-', label=sport)
    ax.set_title("Évolution de la Vitesse Moyenne (km/h) par Sport", fontsize=16)
    ax.set_xlabel("Année")
    ax.set_ylabel("Vitesse Moyenne (km/h)")
    ax.legend(title="Sport")
    ax.grid(True)
    plt.tight_layout()
    file_name = os.path.join(save_path, "strava_avg_speed_sport_yearly.png")
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Graphique sauvegardé : {file_name}")

# ----------------------------------------------------------------------------------
# 4. NOUVELLES FONCTIONS : Volume Mensuel (InchAngées)
# ----------------------------------------------------------------------------------

def aggregate_volume_monthly(df):
    if df.empty: return pd.DataFrame()
    df_monthly = df.groupby(['year', 'month']).agg(
        total_distance_km=('distance_km', 'sum')
    ).reset_index()
    return df_monthly

def plot_volume_monthly(df_monthly, save_path):
    if df_monthly.empty:
        print("Aucune donnée de volume mensuel à afficher.")
        return
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(12, 6))
    df_monthly['year_month'] = df_monthly['year'].astype(str) + '-' + df_monthly['month'].apply(lambda x: f'{x:02d}')
    ax.plot(df_monthly['year_month'], df_monthly['total_distance_km'], marker='.', linestyle='-', color='indigo')
    unique_years = df_monthly['year'].unique()
    x_ticks_pos = [df_monthly[df_monthly['year'] == y]['year_month'].iloc[0] for y in unique_years]
    ax.set_xticks(x_ticks_pos)
    ax.set_xticklabels(unique_years, rotation=45, ha='right')
    ax.set_title("Volume d'Entraînement Cumulé (Distance) par Mois", fontsize=16)
    ax.set_ylabel("Distance Totale (km)")
    ax.set_xlabel("Année")
    ax.grid(True, axis='y')
    plt.tight_layout()
    file_name = os.path.join(save_path, "strava_volume_monthly.png")
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Graphique sauvegardé : {file_name}")

# ----------------------------------------------------------------------------------
# 5. NOUVELLES FONCTIONS : Heatmap d'Activité (InchAngées)
# ----------------------------------------------------------------------------------

def aggregate_activity_heatmap_data(df):
    if df.empty: return pd.DataFrame()
    df_heatmap = df.pivot_table(
        values='id', index='day_of_week', columns='month', aggfunc='count'
    ).fillna(0)
    day_names = [calendar.day_name[i] for i in range(7)]
    df_heatmap.index = pd.CategoricalIndex([day_names[i] for i in df_heatmap.index], categories=day_names, ordered=True)
    df_heatmap.sort_index(level=0, inplace=True)
    df_heatmap.columns = [calendar.month_abbr[i] for i in df_heatmap.columns]
    return df_heatmap

def plot_activity_heatmap(df_heatmap, save_path):
    if df_heatmap.empty:
        print("Aucune donnée pour la heatmap à afficher.")
        return
    plt.figure(figsize=(12, 6))
    sns.heatmap(df_heatmap, annot=True, fmt="g", linewidths=.5, cmap="viridis", cbar_kws={'label': 'Nombre Total d\'Activités'})
    plt.title("Régularité d'Entraînement : Nombre d'Activités (Jours x Mois)", fontsize=16)
    plt.xlabel("Mois")
    plt.ylabel("Jour de la Semaine")
    plt.yticks(rotation=0)
    plt.tight_layout()
    file_name = os.path.join(save_path, "strava_activity_heatmap.png")
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Graphique sauvegardé : {file_name}")


def aggregate_distance_by_day_and_month(df):
    """
    Calcule la distance totale cumulée par jour de la semaine et par mois, toutes années confondues.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Agrégation par Jour de la Semaine
    df_day = df.groupby('day_of_week').agg(
        total_distance_km=('distance_km', 'sum')
    ).reset_index()

    # Agrégation par Mois
    df_month = df.groupby('month').agg(
        total_distance_km=('distance_km', 'sum')
    ).reset_index()

    return df_day, df_month

def plot_distance_by_day_of_week(df_day, save_path):
    """
    Génère un graphique à barres du kilométrage cumulé par jour de la semaine.
    """
    if df_day.empty:
        print("Aucune donnée de distance par jour de la semaine à afficher.")
        return

    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(10, 6))

    # Noms des jours en français pour l'axe X (basés sur 0=Lundi)
    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    
    # Assurez-vous que les données sont ordonnées du Lundi au Dimanche
    df_day['day_name'] = df_day['day_of_week'].apply(lambda x: day_names[x])

    ax.bar(df_day['day_name'], df_day['total_distance_km'], color='teal')
    
    ax.set_title("Distance Cumulée (km) par Jour de la Semaine (Toutes Années)", fontsize=14)
    ax.set_xlabel("Jour de la Semaine")
    ax.set_ylabel("Distance Totale (km)")
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    file_name = os.path.join(save_path, "strava_total_distance_by_day.png")
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Graphique sauvegardé : {file_name}")


def plot_distance_by_month_total(df_month, save_path):
    """
    Génère un graphique à barres du kilométrage cumulé par mois, toutes années confondues.
    """
    if df_month.empty:
        print("Aucune donnée de distance par mois à afficher.")
        return

    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(10, 6))

    # Noms des mois en français pour l'axe X (basés sur 1=Janvier)
    month_names = [calendar.month_abbr[i] for i in range(1, 13)]
    
    # Assurez-vous que l'ordre des mois est correct (1 à 12)
    df_month = df_month.sort_values(by='month')

    ax.bar(df_month['month'].apply(lambda x: month_names[x - 1]), # Utilise l'abréviation du mois
           df_month['total_distance_km'], 
           color='sienna')
    
    ax.set_title("Distance Cumulée (km) par Mois (Toutes Années)", fontsize=14)
    ax.set_xlabel("Mois")
    ax.set_ylabel("Distance Totale (km)")
    
    plt.tight_layout()
    
    file_name = os.path.join(save_path, "strava_total_distance_by_month.png")
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Graphique sauvegardé : {file_name}")

def aggregate_distance_histogram_data(df):
    """
    Prépare les données pour l'histogramme (pas de véritable agrégation nécessaire,
    on retourne simplement la colonne des distances).
    """
    if df.empty:
        return pd.Series(dtype='float64')
    
    # On filtre les valeurs aberrantes (ex: activités de moins de 1 km qui fausseraient l'histogramme)
    # et on retourne la colonne de distance.
    return df[df['distance_km'] >= 1]['distance_km']

def plot_distance_histogram(distance_series, save_path):
    """
    Génère un histogramme montrant la fréquence de chaque distance d'activité, 
    en utilisant des intervalles de 10 km.
    """
    if distance_series.empty:
        print("Aucune donnée de distance valide pour l'histogramme à afficher.")
        return

    plt.style.use('seaborn-v0_8-darkgrid')
    # Augmente la taille de la figure pour une meilleure lisibilité
    fig, ax = plt.subplots(figsize=(15, 7)) 

    # --- MODIFICATION CLÉ : Définition des "bins" (intervalles) ---
    bin_width = 10
    max_dist = int(distance_series.max())
    
    # On définit la limite supérieure pour qu'elle soit un multiple de 10
    plot_limit = (max_dist // bin_width + 1) * bin_width
    
    # Création des intervalles (0-10, 10-20, 20-30, etc.)
    bins = range(0, plot_limit + bin_width, bin_width) 
    
    # ---------------------------------------------------------------

    ax.hist(distance_series, bins=bins, color='darkgreen', edgecolor='black', alpha=0.7)
    
    ax.set_title("Distribution des Distances d'Activités (Toutes Années)", fontsize=16)
    ax.set_xlabel(f"Distance (km) - Intervalle de {bin_width} km")
    ax.set_ylabel("Fréquence (Nombre d'Activités)")
    
    # Afficher les étiquettes de l'axe X pour chaque intervalle de 10 km
    plt.xticks(bins, rotation=45, ha='right') 
    plt.xlim(0, plot_limit)
    
    plt.tight_layout()
    
    file_name = os.path.join(save_path, "strava_distance_histogram.png")
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Graphique sauvegardé : {file_name}")

def aggregate_everesting_data(df):
    """
    Calcule le dénivelé positif cumulé par activité dans l'ordre chronologique.
    """
    if df.empty:
        return pd.DataFrame()

    # S'assurer que le DataFrame est trié par date pour une progression correcte
    df_sorted = df.sort_values(by='start_date')
    
    # Calculer le D+ cumulé
    df_sorted['cumulative_elevation_m'] = df_sorted['total_elevation_gain'].cumsum()
    
    return df_sorted[['start_date', 'cumulative_elevation_m']]

def plot_everesting_progression(df_everesting, save_path):
    """
    Génère un graphique linéaire de la progression du D+ cumulé avec les seuils de l'Everesting.
    """
    if df_everesting.empty:
        print("Aucune donnée de dénivelé pour la progression Everesting à afficher.")
        return

    plt.style.use('seaborn-v0_8-darkgrid')
    fig, ax = plt.subplots(figsize=(12, 6))

    # Constantes pour l'Everesting
    EVEREST_HEIGHT_M = 8848
    
    # Tracer la courbe de progression
    ax.plot(df_everesting['start_date'], df_everesting['cumulative_elevation_m'], 
            label='D+ Cumulé', color='darkblue', linewidth=2)

    # Ajouter les lignes horizontales (Seuils d'Everesting)
    levels = [
        (EVEREST_HEIGHT_M, 'Everesting (8848 m)', 'r--'),
        (EVEREST_HEIGHT_M * 2, 'Double Everesting (17696 m)', 'r--'),
        # Vous pouvez ajouter d'autres seuils ici si vous le souhaitez
    ]
    
    for height, label, style in levels:
        if df_everesting['cumulative_elevation_m'].max() > height * 0.5: # N'affiche que si vous avez dépassé 50% du seuil
            ax.axhline(y=height, color=style[0], linestyle=style[1], linewidth=1, 
                       label=label, alpha=0.7)
            # Annoter la ligne
            ax.text(df_everesting['start_date'].iloc[-1], height + height * 0.01, label, 
                    color=style[0], ha='right', va='bottom')


    ax.set_title("Progression du Dénivelé Positif Cumulé ('Everesting')", fontsize=16)
    ax.set_xlabel("Date")
    ax.set_ylabel("Dénivelé Positif Cumulé (m)")
    ax.legend(loc='upper left')
    ax.grid(True)
    
    plt.tight_layout()
    
    file_name = os.path.join(save_path, "strava_everesting_progression.png")
    plt.savefig(file_name, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"Graphique sauvegardé : {file_name}")

# Chargement des données 
athlete_id = 18278258
activities = load_existing_activities(athlete_id)

df_activities = prepare_data(activities)

# Définir le chemin de sauvegarde en utilisant la fonction fournie
save_directory = graph_dir(athlete_id)

if not df_activities.empty:
    
    # --- GRAPHIQUES 1-4 : Évolution Annuelle (existant) ---
    df_yearly_stats = aggregate_yearly_data(df_activities)
    if not df_yearly_stats.empty:
        print("--- SYNTHÈSE ANNUELLE ---")
        print(df_yearly_stats.to_string(index=False, float_format="%.0f")) 
        print("-" * 40)
        plot_yearly_evolution_separate(df_yearly_stats, save_directory)

    # --- GRAPHIQUE 5 : Vitesse Moyenne Annuelle par Sport ---
    df_avg_speed_stats = aggregate_avg_performance_by_sport(df_activities)
    if not df_avg_speed_stats.empty:
        plot_avg_speed_per_sport_yearly(df_avg_speed_stats, save_directory)

    # --- GRAPHIQUE 6 : Volume Mensuel ---
    df_monthly_volume = aggregate_volume_monthly(df_activities)
    if not df_monthly_volume.empty:
        plot_volume_monthly(df_monthly_volume, save_directory)

    # --- GRAPHIQUE 7 : Heatmap d'Activité (Jours x Mois) ---
    df_heatmap_data = aggregate_activity_heatmap_data(df_activities)
    if not df_heatmap_data.empty:
        plot_activity_heatmap(df_heatmap_data, save_directory)

    df_day_dist, df_month_dist = aggregate_distance_by_day_and_month(df_activities)

    if not df_day_dist.empty:
        plot_distance_by_day_of_week(df_day_dist, save_directory)

    if not df_month_dist.empty:
        plot_distance_by_month_total(df_month_dist, save_directory)


    distance_series = aggregate_distance_histogram_data(df_activities)
    if not distance_series.empty:
        plot_distance_histogram(distance_series, save_directory)

    df_everesting_data = aggregate_everesting_data(df_activities)
    if not df_everesting_data.empty:
        plot_everesting_progression(df_everesting_data, save_directory)

else:
    print("Processus terminé : Aucune donnée à analyser après le chargement.")