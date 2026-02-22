from PIL import Image
import os

src = "static/img/ai/фавикон нов.png"
img = Image.open(src).convert("RGBA")
print(f"Исходный: {img.size}")

# Фон прозрачный (alpha=0). Ищем bbox по alpha > 50 (включая тени/свечение)
alpha = img.split()[3]
# Порог 50 - включаем полутени
thresholded = alpha.point(lambda x: 255 if x > 50 else 0)
bb = thresholded.getbbox()
print(f"bbox (alpha>50): {bb}")

# Небольшой padding
pad = 4
x0 = max(0, bb[0] - pad)
y0 = max(0, bb[1] - pad)
x1 = min(img.width, bb[2] + pad)
y1 = min(img.height, bb[3] + pad)
cropped = img.crop((x0, y0, x1, y1))
print(f"После кропа: {cropped.size}")

# Квадрат с белым фоном, композитинг
w, h = cropped.size
side = max(w, h)
square = Image.new("RGBA", (side, side), (255, 255, 255, 255))
offset = ((side - w) // 2, (side - h) // 2)
square.paste(cropped, offset, cropped)
square_rgb = square.convert("RGB")

# Генерируем размеры
sizes_px = [128, 64, 48, 32, 16]
imgs = [square_rgb.resize((s, s), Image.LANCZOS) for s in sizes_px]

# ICO
imgs[0].save(
    "static/img/favicon.ico",
    format="ICO",
    sizes=[(s, s) for s in sizes_px],
    append_images=imgs[1:]
)
print("favicon.ico:", os.path.getsize("static/img/favicon.ico"), "байт")

square_rgb.resize((32, 32), Image.LANCZOS).save("static/img/favicon-32.png")
square_rgb.resize((192, 192), Image.LANCZOS).save("static/img/favicon-192.png")
print("Готово")
