import urllib.request
import json
import time
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import pandas as pd
import numpy as np

GENRE_QUERIES = [
    ("Rock", ["rock classics", "hard rock", "alternative rock", "indie rock", "classic rock hits"]),
    ("Hip-Hop", ["hip hop classics", "rap greatest hits", "trap music", "conscious rap", "hip hop 2020s"]),
    ("R&B / Soul", ["r&b soul classics", "contemporary r&b", "neo soul", "motown soul"]),
    ("Country", ["country hits", "classic country", "modern country", "nashville country"]),
    ("Electronic", ["electronic dance", "house music", "edm hits", "ambient synth", "techno"]),
    ("Latin", ["latin pop hits", "reggaeton classics", "musica latina", "salsa hits"]),
    ("Jazz", ["jazz classics", "modern jazz", "blue note jazz", "smooth jazz", "bossa nova jazz"]),
]

def search_itunes(term, genre_label):
    encoded = urllib.parse.quote(term)
    url = f"https://itunes.apple.com/search?term={encoded}&entity=album&limit=30"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            results = []
            for item in data.get("results", []):
                results.append({
                    "artist": item.get("artistName"),
                    "album": item.get("collectionName"),
                    "year": int(item.get("releaseDate", "2020")[:4]),
                    "tracks": item.get("trackCount", 10),
                    "genre": genre_label,
                    "cover_thumbnail": item.get("artworkUrl100"),
                    "cover_full": item.get("artworkUrl100", "").replace("100x100bb.jpg", "600x600bb.jpg")
                })
            return results
    except Exception as e:
        print(f"Error fetching {term}: {e}")
        return []

def extract_visual_features(row):
    url = row.get("cover_thumbnail")
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            img = Image.open(resp).convert("RGB").resize((32, 32))
            arr = np.array(img, dtype=float)
            r, g, b = arr[:,:,0].mean(), arr[:,:,1].mean(), arr[:,:,2].mean()
            brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0 * 100
            
            max_c = np.max(arr, axis=2)
            min_c = np.min(arr, axis=2)
            delta = max_c - min_c
            sat = np.where(max_c == 0, 0, delta / (max_c + 1e-6)).mean() * 100
            
            gray = 0.299 * arr[:,:,0] + 0.587 * arr[:,:,1] + 0.114 * arr[:,:,2]
            contrast = gray.std()
            
            if brightness < 25:
                palette = "Dark & Moody"
            elif brightness > 75 and sat < 20:
                palette = "Minimalist White"
            elif sat < 18:
                palette = "Monochrome / Gray"
            elif r > g and r > b:
                palette = "Pink & Magenta" if b > g else "Warm Red & Orange"
            elif b > r and b > g:
                palette = "Cool Blue"
            elif g > r and g > b:
                palette = "Green"
            else:
                palette = "Warm Yellow & Gold"
                
            res = dict(row)
            res.update({
                "brightness": round(brightness, 1),
                "saturation": round(sat, 1),
                "contrast": round(contrast, 1),
                "palette": palette,
                "hex_color": f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            })
            return res
    except Exception as e:
        return None

if __name__ == "__main__":
    import urllib.parse
    print("Fetching albums across different genres...")
    all_raw = []
    for genre_label, queries in GENRE_QUERIES:
        for q in queries:
            print(f"Searching {genre_label}: {q}...")
            items = search_itunes(q, genre_label)
            all_raw.extend(items)
            time.sleep(0.3)
            
    print(f"Total raw fetched: {len(all_raw)}")
    # Deduplicate raw
    df_raw = pd.DataFrame(all_raw).dropna(subset=["artist", "album", "cover_thumbnail"])
    df_raw = df_raw.drop_duplicates(subset=["artist", "album"]).reset_index(drop=True)
    print(f"Unique fetched: {len(df_raw)}")
    
    # Existing albums
    existing_df = pd.read_csv("pop_albums.csv")
    existing_keys = set(zip(existing_df["artist"].str.lower(), existing_df["album"].str.lower()))
    
    to_process = [r for _, r in df_raw.iterrows() if (str(r["artist"]).lower(), str(r["album"]).lower()) not in existing_keys]
    print(f"New albums to analyze features: {len(to_process)}")
    
    enriched = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for res in executor.map(extract_visual_features, to_process):
            if res:
                enriched.append(res)
                
    print(f"Successfully enriched {len(enriched)} new albums!")
    if enriched:
        new_df = pd.DataFrame(enriched)
        combined = pd.concat([existing_df, new_df]).drop_duplicates(subset=["artist", "album"]).reset_index(drop=True)
        # Normalize genres: make sure Pop variants are unified under "Pop"
        combined["genre"] = combined["genre"].replace({
            "K-Pop": "Pop",
            "Indie Pop": "Pop",
            "Pop Latino": "Latin",
            "J-Pop": "Pop",
            "French Pop": "Pop",
            "Pop/Rock": "Pop",
            "Indian Pop": "Pop",
            "Christian Pop": "Pop",
            "Christmas: Pop": "Pop",
            "Afro-Pop": "Pop",
            "Vocal Pop": "Pop"
        })
        print(f"Combined total albums: {len(combined)}")
        print(combined["genre"].value_counts())
        combined.to_csv("pop_albums.csv", index=False)
        print("Updated pop_albums.csv successfully!")
