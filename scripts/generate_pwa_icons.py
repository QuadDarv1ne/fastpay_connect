"""
Генератор иконок для PWA из SVG
Запустите этот скрипт для создания всех необходимых иконок
"""

import os
from pathlib import Path

# Базовые размеры иконок
ICON_SIZES = [
    72,
    96,
    128,
    144,
    152,
    192,
    384,
    512,
]

# Бейдж для уведомлений
BADGE_SIZES = [72, 96]

# Shortcut иконки
SHORTCUT_SIZES = [96, 192]


def generate_icons():
    """Сгенерировать все иконки."""
    base_dir = Path(__file__).parent
    icons_dir = base_dir / "icons"
    
    # Создаём директорию если не существует
    icons_dir.mkdir(exist_ok=True)
    
    print(f"Генерация иконок в {icons_dir}")
    
    # Для генерации PNG из SVG нужен PIL/Pillow или cairosvg
    try:
        from PIL import Image, ImageDraw
        import svglib.svg_lib as svglib
        from reportlab.graphics import renderPM
        
        for size in ICON_SIZES:
            svg_path = icons_dir / "icon.svg"
            png_path = icons_dir / f"icon-{size}x{size}.png"
            
            # Конвертация SVG в PNG
            try:
                drawing = svglib.svg_lib.svg2rlg(str(svg_path))
                renderPM.drawToFile(drawing, str(png_path), fmt="PNG")
                print(f"✓ icon-{size}x{size}.png")
            except Exception as e:
                print(f"✗ icon-{size}x{size}.png: {e}")
                
    except ImportError:
        print("\nДля генерации иконок установите:")
        print("  pip install Pillow svglib reportlab")
        print("\nИли используйте онлайн-конвертер SVG в PNG")
        print(f"Базовый SVG находится в: {icons_dir / 'icon.svg'}")
    
    # Создаём placeholder для бейджа
    create_badge_placeholder(icons_dir)
    
    # Создаём placeholder для shortcut иконок
    create_shortcut_placeholders(icons_dir)
    
    print("\n✓ Генерация иконок завершена!")


def create_badge_placeholder(icons_dir):
    """Создать placeholder для бейджа уведомлений."""
    try:
        from PIL import Image, ImageDraw
        
        for size in BADGE_SIZES:
            img = Image.new('RGBA', (size, size), (0, 150, 136, 255))
            draw = ImageDraw.Draw(img)
            
            # Рисуем колокольчик
            center = size // 2
            radius = size // 3
            
            draw.ellipse(
                [center - radius, center - radius, center + radius, center + radius],
                fill='#FFFFFF'
            )
            
            img.save(icons_dir / f"badge-{size}x{size}.png")
            print(f"✓ badge-{size}x{size}.png")
            
    except ImportError:
        print(f"✗ badge placeholder: PIL not installed")


def create_shortcut_placeholders(icons_dir):
    """Создать placeholder для shortcut иконок."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        shortcuts = [
            ("payments", "₽", "#009688"),
            ("webhooks", "🔔", "#FF9800"),
            ("admin", "⚙️", "#607D8B"),
        ]
        
        for name, symbol, color in shortcuts:
            for size in SHORTCUT_SIZES:
                img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
                draw = ImageDraw.Draw(img)
                
                # Рисуем круг
                margin = size // 8
                draw.ellipse(
                    [margin, margin, size - margin, size - margin],
                    fill=color
                )
                
                # Рисуем символ (если есть шрифт)
                try:
                    font = ImageFont.truetype("arial.ttf", size // 2)
                    text_bbox = draw.textbbox((0, 0), symbol, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    x = (size - text_width) // 2
                    y = (size - text_height) // 2
                    draw.text((x, y), symbol, fill='#FFFFFF', font=font)
                except:
                    # Без шрифта
                    pass
                
                img.save(icons_dir / f"shortcut-{name}-{size}x{size}.png")
                print(f"✓ shortcut-{name}-{size}x{size}.png")
                
    except ImportError:
        print(f"✗ shortcut placeholders: PIL not installed")


if __name__ == "__main__":
    generate_icons()
