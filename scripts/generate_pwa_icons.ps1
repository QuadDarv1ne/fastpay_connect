# Генерация PWA иконок для FastPay Connect
# Автор: Dupley Maxim Igorevich
# © 2026 Dupley Maxim Igorevich. Все права защищены.
# Запустите этот скрипт в PowerShell для создания всех иконок

$iconsDir = "C:\Users\maksi\OneDrive\Documents\GitHub\fastpay_connect\app\static\icons"

# Размеры иконок
$sizes = @(72, 96, 128, 144, 152, 192, 384, 512)

Write-Host "Генерация иконок в $iconsDir" -ForegroundColor Green

# Проверяем, существует ли директория
if (-not (Test-Path $iconsDir)) {
    New-Item -ItemType Directory -Path $iconsDir | Out-Null
}

# Создаём простые PNG иконки (базовый цвет)
foreach ($size in $sizes) {
    $filename = "icon-${size}x${size}.png"
    $filepath = Join-Path $iconsDir $filename
    
    # Создаём bitmap с градиентом
    $bitmap = New-Object System.Drawing.Bitmap($size, $size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    
    # Градиентный фон
    $brush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        (New-Object System.Drawing.Rectangle(0, 0, $size, $size)),
        [System.Drawing.Color]::FromArgb(0, 150, 136),
        [System.Drawing.Color]::FromArgb(0, 121, 107),
        45
    )
    
    $graphics.FillRectangle($brush, 0, 0, $size, $size)
    
    # Рисуем белую карточку
    $cardMargin = [int]($size * 0.2)
    $cardWidth = $size - (2 * $cardMargin)
    $cardHeight = [int]($size * 0.4)
    $cardX = $cardMargin
    $cardY = [int]($size * 0.3)
    
    $cardBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(240, 255, 255, 255))
    $graphics.FillRectangle($cardBrush, $cardX, $cardY, $cardWidth, $cardHeight)
    
    # Рисуем текст "FP"
    $font = New-Object System.Drawing.Font("Arial", [float]($size * 0.3), [System.Drawing.FontStyle]::Bold)
    $stringFormat = New-Object System.Drawing.StringFormat()
    $stringFormat.Alignment = [System.Drawing.StringAlignment]::Center
    $stringFormat.LineAlignment = [System.Drawing.StringAlignment]::Center
    
    $textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 255, 255, 255))
    $graphics.DrawString("FP", $font, $textBrush, 
        (New-Object System.Drawing.RectangleF(0, [float]($size * 0.75), $size, [float]($size * 0.2))), 
        $stringFormat)
    
    # Сохраняем
    $bitmap.Save($filepath)
    $graphics.Dispose()
    $bitmap.Dispose()
    
    Write-Host "✓ $filename" -ForegroundColor Green
}

# Создаём бейджи для уведомлений
$badgeSizes = @(72, 96)
foreach ($size in $badgeSizes) {
    $filename = "badge-${size}x${size}.png"
    $filepath = Join-Path $iconsDir $filename
    
    $bitmap = New-Object System.Drawing.Bitmap($size, $size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    
    # Оранжевый фон
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 152, 0))
    $graphics.FillRectangle($brush, 0, 0, $size, $size)
    
    # Рисуем колокольчик (упрощённо - круг)
    $center = $size / 2
    $radius = $size / 4
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::White, [int]($size / 15))
    $graphics.DrawEllipse($pen, $center - $radius, $center - $radius, $radius * 2, $radius * 2)
    
    $bitmap.Save($filepath)
    $graphics.Dispose()
    $bitmap.Dispose()
    
    Write-Host "✓ $filename" -ForegroundColor Green
}

# Создаём shortcut иконки
$shortcuts = @(
    @{ Name = "payments"; Symbol = "₽"; Color = [System.Drawing.Color]::FromArgb(0, 150, 136) },
    @{ Name = "webhooks"; Symbol = "!"; Color = [System.Drawing.Color]::FromArgb(255, 152, 0) },
    @{ Name = "admin"; Symbol = "⚙"; Color = [System.Drawing.Color]::FromArgb(96, 125, 139) }
)

$shortcutSizes = @(96, 192)
foreach ($shortcut in $shortcuts) {
    foreach ($size in $shortcutSizes) {
        $filename = "shortcut-$($shortcut.Name)-${size}x${size}.png"
        $filepath = Join-Path $iconsDir $filename
        
        $bitmap = New-Object System.Drawing.Bitmap($size, $size)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        
        # Белый фон
        $graphics.Clear([System.Drawing.Color]::White)
        
        # Цветной круг
        $margin = [int]($size * 0.15)
        $brush = New-Object System.Drawing.SolidBrush($shortcut.Color)
        $graphics.FillEllipse($brush, $margin, $margin, $size - (2 * $margin), $size - (2 * $margin))
        
        # Символ
        try {
            $font = New-Object System.Drawing.Font("Arial", [float]($size * 0.5), [System.Drawing.FontStyle]::Bold)
            $stringFormat = New-Object System.Drawing.StringFormat()
            $stringFormat.Alignment = [System.Drawing.StringAlignment]::Center
            $stringFormat.LineAlignment = [System.Drawing.StringAlignment]::Center
            
            $textBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
            $graphics.DrawString($shortcut.Symbol, $font, $textBrush, 
                (New-Object System.Drawing.RectangleF(0, 0, $size, $size)), 
                $stringFormat)
        } catch {
            # Игнорируем ошибки шрифтов
        }
        
        $bitmap.Save($filepath)
        $graphics.Dispose()
        $bitmap.Dispose()
        
        Write-Host "✓ $filename" -ForegroundColor Green
    }
}

Write-Host "`n✓ Генерация иконок завершена!" -ForegroundColor Green
Write-Host "Иконки созданы в: $iconsDir" -ForegroundColor Cyan
