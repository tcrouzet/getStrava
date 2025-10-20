# heatmap_png.py
# python3 ./app/heatmap.py

# import glob, gpxpy
# import numpy as np
# from tqdm import tqdm
# from PIL import Image
# import matplotlib.pyplot as plt
# from scipy.ndimage import gaussian_filter
# from storage import gpx_dir, heatmap_path

import glob, gpxpy
import numpy as np
from tqdm import tqdm
from PIL import Image
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from storage import gpx_dir, heatmap_dir

# Paramètres
LAT_STEP = 0.5  # 0.5° latitude par tuile
LON_STEP = 0.5  # 0.5° longitude par tuile
TILE_SIZE_PX = (2000, 2000)
BLUR = 4
SAMPLE_EVERY = 50

def all_points(gpx_dir):
    pts = []
    for path in tqdm(glob.glob(f"{gpx_dir}/**/*.gpx", recursive=True)):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                gpx = gpxpy.parse(f)
            for tr in gpx.tracks:
                for seg in tr.segments:
                    for i, p in enumerate(seg.points):
                        if i % SAMPLE_EVERY == 0:
                            pts.append((p.latitude, p.longitude))
        except Exception:
            pass
    return np.array(pts)

def tile_index(lat, lon):
    return int(lat // LAT_STEP), int(lon // LON_STEP)

def render_tiles(pts, heatmap_dir):
    tiles = {}
    for lat, lon in pts:
        iy, ix = tile_index(lat, lon)
        tiles.setdefault((iy, ix), []).append((lat, lon))

    for (iy, ix), tile_pts in tiles.items():
        tile_pts = np.array(tile_pts)
        lat_min, lon_min = tile_pts.min(axis=0)
        lat_max, lon_max = tile_pts.max(axis=0)

        x = ((tile_pts[:,1]-lon_min)/(lon_max-lon_min)*(TILE_SIZE_PX[0]-1)).astype(int)
        y = TILE_SIZE_PX[1]-1 - ((tile_pts[:,0]-lat_min)/(lat_max-lat_min)*(TILE_SIZE_PX[1]-1)).astype(int)

        heat = np.zeros(TILE_SIZE_PX[::-1], dtype=np.float32)
        np.add.at(heat, (y, x), 1)
        heat = gaussian_filter(heat, sigma=BLUR)
        heat /= heat.max()
        img = np.uint8(plt.cm.plasma(heat)*255)
        output_path = f"{heatmap_dir}/tile_{iy}_{ix}.png"
        Image.fromarray(img).save(output_path)
        print(f"→ {output_path}")

if __name__ == "__main__":
    athlete_id = 18278258
    pts = all_points(gpx_dir(athlete_id))
    render_tiles(pts, heatmap_dir(athlete_id))
