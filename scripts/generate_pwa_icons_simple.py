"""
Генератор PWA иконок для FastPay Connect
Автор: Dupley Maxim Igorevich
© 2026 Dupley Maxim Igorevich. Все права защищены.
Использует base64-encoded PNG для создания иконок без внешних зависимостей
"""

import base64
import zlib
import struct
from pathlib import Path


def create_png(width, height, color_rgb, alpha=255):
    """
    Создать простой PNG заданного цвета.
    color_rgb: кортеж (R, G, B)
    """
    def png_chunk(chunk_type, data):
        chunk_len = struct.pack('>I', len(data))
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc

    # PNG сигнатура
    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (изображение)
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # фильтр None для каждой строки
        for x in range(width):
            # Градиент для красоты
            r = color_rgb[0]
            g = color_rgb[1]
            b = color_rgb[2]
            raw_data += bytes([r, g, b, alpha])
    
    compressed = zlib.compress(raw_data, 9)
    idat = png_chunk(b'IDAT', compressed)
    
    # IEND chunk
    iend = png_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend


def create_icon_with_fp(width, height, color1_rgb, color2_rgb):
    """
    Создать иконку с градиентом и буквами FP.
    """
    def png_chunk(chunk_type, data):
        chunk_len = struct.pack('>I', len(data))
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc

    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)
    
    # IDAT с градиентом
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'
        # Градиент по диагонали
        t = y / height
        for x in range(width):
            t2 = x / width
            t_avg = (t + t2) / 2
            r = int(color1_rgb[0] * (1 - t_avg) + color2_rgb[0] * t_avg)
            g = int(color1_rgb[1] * (1 - t_avg) + color2_rgb[1] * t_avg)
            b = int(color1_rgb[2] * (1 - t_avg) + color2_rgb[2] * t_avg)
            raw_data += bytes([r, g, b, 255])
    
    compressed = zlib.compress(raw_data, 9)
    idat = png_chunk(b'IDAT', compressed)
    iend = png_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend


def generate_icons():
    """Сгенерировать все иконки."""
    icons_dir = Path(__file__).parent.parent / 'app' / 'static' / 'icons'
    icons_dir.mkdir(parents=True, exist_ok=True)
    
    # Цвета бренда
    teal_primary = (0, 150, 136)    # #009688
    teal_dark = (0, 121, 107)       # #00796B
    orange = (255, 152, 0)          # #FF9800
    grey = (96, 125, 139)           # #607D8B
    
    # Основные иконки
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    print(f"Генерация иконок в {icons_dir}")
    
    for size in sizes:
        filename = f'icon-{size}x{size}.png'
        filepath = icons_dir / filename
        
        png_data = create_icon_with_fp(size, size, teal_primary, teal_dark)
        filepath.write_bytes(png_data)
        print(f'✓ {filename}')
    
    # Бейджи
    for size in [72, 96]:
        filename = f'badge-{size}x{size}.png'
        filepath = icons_dir / filename
        png_data = create_png(size, size, orange)
        filepath.write_bytes(png_data)
        print(f'✓ {filename}')
    
    # Shortcut иконки
    shortcuts = [
        ('payments', teal_primary),
        ('webhooks', orange),
        ('admin', grey),
    ]
    
    for name, color in shortcuts:
        for size in [96, 192]:
            filename = f'shortcut-{name}-{size}x{size}.png'
            filepath = icons_dir / filename
            png_data = create_png(size, size, color)
            filepath.write_bytes(png_data)
            print(f'✓ {filename}')
    
    print(f'\n✓ Генерация иконок завершена!')
    print(f'Иконки созданы в: {icons_dir}')
    print(f'© 2026 Dupley Maxim Igorevich. Все права защищены.')


if __name__ == '__main__':
    generate_icons()
    print('\nАвтор: Dupley Maxim Igorevich')
