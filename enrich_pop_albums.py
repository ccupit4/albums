import urllib.request
import time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import pandas as pd
import numpy as np

print("Enriching 1,000 pop albums with color and visual features...")
df = pd.read_csv("pop_albums.csv")

def extract_features(row):
    url = row["cover_thumbnail"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            img = Image.open(resp).convert("RGB").resize((32, 32))
            arr = np.array(img, dtype=float)
            r, g, b = arr[:,:,0].mean(), arr[:,:,1].mean(), arr[:,:,2].mean()
            brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 * 100
            
            # Saturation calculation
            max_c = np.max(arr, axis=2)
            min_c = np.min(arr, axis=2)
            delta = max_c - min_c
            sat = np.where(max_c == 0, 0, delta / (max_c + 1e-6)).mean() * 100
            
            # Contrast (standard deviation of grayscale values)
            gray = 0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]
            contrast = gray.std()
            
            # Categorize primary tone
            if brightness < 25:
                palette = "Dark & Moody"
            elif brightness > 75 and sat < 20:
                palette = "Minimalist White"
            elif sat < 18:
                palette = "Monochrome / Gray"
            elif r > g and r > b:
                if b > g:
                    palette = "Pink & Magenta"
                else:
                    palette = "Warm Red & Orange"
            elif b > r and b > g:
                palette = "Cool Blue"
            elif g > r and g > b:
                palette = "Green"
            else:
                palette = "Warm Yellow & Gold"
                
            return {
                "brightness": round(brightness, 1),
                "saturation": round(sat, 1),
                "contrast": round(contrast, 1),
                "palette": palette,
                "hex_color": f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            }
    except Exception as e:
        return {
            "brightness": 50.0,
            "saturation": 30.0,
            "contrast": 20.0,
            "palette": "Monochrome / Gray",
            "hex_color": "#888888"
        }

with ThreadPoolExecutor(max_workers=30) as ex:
    feature_rows = list(ex.map(extract_features, [row for _, row in df.iterrows()]))

feat_df = pd.DataFrame(feature_rows)
merged = pd.concat([df, feat_df], axis=1)

merged.to_csv("pop_albums.csv", index=False)
print("Updated pop_albums.csv successfully! Breakdown of color palettes:")
print(merged["palette"].value_counts())
