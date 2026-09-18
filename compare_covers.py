import json
import urllib.request
import os
import re
import numpy as np
import pandas as pd
from PIL import Image

os.makedirs("images", exist_ok=True)

# 1. Fetch albums directly via artist ID for clean discographies
# RHCP: 889780, Taylor Swift: 159260351
artists = {
    "Taylor Swift": "159260351",
    "Red Hot Chili Peppers": "889780"
}

albums = []
for artist_name, artist_id in artists.items():
    url = f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=100"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode())["results"]
    for item in data[1:]:  # skip artist item
        if item.get("wrapperType") == "collection" and item.get("collectionType") == "Album":
            title = item.get("collectionName", "")
            # filter out singles, karaoke, and live bootlegs
            if item.get("trackCount", 0) >= 6 and not any(k in title.lower() for k in ["karaoke", "live from", "session"]):
                clean_title = re.sub(r"\s*\(.*?\)", "", title).strip()
                art_url = item.get("artworkUrl100", "").replace("100x100bb.jpg", "600x600bb.jpg")
                albums.append({
                    "artist": artist_name,
                    "title": title,
                    "clean_title": clean_title,
                    "release_date": item.get("releaseDate", "")[:10],
                    "artwork_url": art_url
                })

df = pd.DataFrame(albums).drop_duplicates(subset=["artist", "clean_title"]).copy()

# Keep top 10 iconic studio albums for each artist for a clear, focused comparison
selected = df.groupby("artist").head(10).reset_index(drop=True)

# 2. Download images and extract color + design features
features = []
for idx, row in selected.iterrows():
    img_path = f"images/{idx:02d}_{row['artist'][:3]}_{re.sub(r'[^a-zA-Z0-9]', '', row['clean_title'])[:12]}.jpg"
    if not os.path.exists(img_path):
        urllib.request.urlretrieve(row["artwork_url"], img_path)
    selected.loc[idx, "image_path"] = img_path
    
    img = Image.open(img_path).convert("RGB")
    
    # Color features: HSV histogram (12 hue bins, 4 sat bins, 4 val bins = 192 features)
    hsv = img.convert("HSV")
    hsv_arr = np.array(hsv)
    h_hist, _ = np.histogram(hsv_arr[:, :, 0], bins=12, range=(0, 256), density=True)
    s_hist, _ = np.histogram(hsv_arr[:, :, 1], bins=4, range=(0, 256), density=True)
    v_hist, _ = np.histogram(hsv_arr[:, :, 2], bins=4, range=(0, 256), density=True)
    color_vec = np.concatenate([h_hist * 2.0, s_hist, v_hist])
    color_vec = color_vec / (np.linalg.norm(color_vec) + 1e-6)
    
    # Design / composition features: low-res spatial structure (16x16 grayscale layout = 256 features)
    gray_thumb = np.array(img.convert("L").resize((16, 16), Image.Resampling.BILINEAR), dtype=float)
    gray_thumb = (gray_thumb - np.mean(gray_thumb)) / (np.std(gray_thumb) + 1e-6)
    design_vec = gray_thumb.flatten()
    design_vec = design_vec / (np.linalg.norm(design_vec) + 1e-6)
    
    # Combined feature vector (weighted: 50% color, 50% spatial design)
    combined = np.concatenate([color_vec, design_vec])
    combined = combined / (np.linalg.norm(combined) + 1e-6)
    features.append((color_vec, design_vec, combined))

# 3. Compute pairwise similarities
pairs = []
n = len(selected)
for i in range(n):
    for j in range(i + 1, n):
        c_sim = float(np.dot(features[i][0], features[j][0]))
        d_sim = float(np.dot(features[i][1], features[j][1]))
        overall_sim = float(np.dot(features[i][2], features[j][2]))
        
        pairs.append({
            "artist1": selected.loc[i, "artist"],
            "title1": selected.loc[i, "clean_title"],
            "img1": selected.loc[i, "image_path"],
            "artist2": selected.loc[j, "artist"],
            "title2": selected.loc[j, "clean_title"],
            "img2": selected.loc[j, "image_path"],
            "same_artist": selected.loc[i, "artist"] == selected.loc[j, "artist"],
            "color_sim": round(c_sim, 3),
            "design_sim": round(d_sim, 3),
            "similarity": round(overall_sim, 3)
        })

pairs_df = pd.DataFrame(pairs).sort_values("similarity", ascending=False)

selected.to_csv("album_metadata.csv", index=False)
pairs_df.to_csv("album_similarity_pairs.csv", index=False)
print("Finished! Top 3 most similar:")
print(pairs_df[["artist1", "title1", "artist2", "title2", "similarity"]].head(3))
print("\nTop 3 least similar:")
print(pairs_df[["artist1", "title1", "artist2", "title2", "similarity"]].tail(3))
