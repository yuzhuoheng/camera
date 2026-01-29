import os
from PIL import Image

def optimize_banners():
    banner_dir = "static/banner"
    if not os.path.exists(banner_dir):
        print(f"Directory {banner_dir} not found.")
        return

    files = os.listdir(banner_dir)
    for file in files:
        if file.endswith(".png") or file.endswith(".jpg"):
            input_path = os.path.join(banner_dir, file)
            # Use the same filename but with .webp extension
            output_path = os.path.join(banner_dir, os.path.splitext(file)[0] + ".webp")
            
            print(f"Optimizing {file}...")
            try:
                with Image.open(input_path) as img:
                    # Convert to WebP with quality 80 (usually plenty for banners)
                    # We also resize if they are excessively large (e.g., > 1920px width)
                    if img.width > 1920:
                        new_height = int((1920 / img.width) * img.height)
                        img = img.resize((1920, new_height), Image.LANCZOS)
                    
                    img.save(output_path, "WEBP", quality=80)
                    
                old_size = os.path.getsize(input_path) / 1024
                new_size = os.path.getsize(output_path) / 1024
                print(f"  Done: {old_size:.1f}KB -> {new_size:.1f}KB (Reduced {100 - (new_size/old_size*100):.1f}%)")
                
                # Optionally delete original PNG to save space
                # os.remove(input_path)
            except Exception as e:
                print(f"  Error optimizing {file}: {e}")

if __name__ == "__main__":
    optimize_banners()
