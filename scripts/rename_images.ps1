# ==========================================
# 图片重命名脚本：追加 _37ac 后缀
# 功能：遍历当前目录及子目录，为未包含 _37ac 的图片添加后缀
# ==========================================

# 1. 定义需要处理的图片扩展名
$extensions = @(".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".svg")

# 2. 获取当前目录及子目录下所有符合扩展名的文件
# -File 确保只获取文件，不包含文件夹
$files = Get-ChildItem -File -Recurse | Where-Object { $extensions -contains $_.Extension.ToLower() }

$count = 0
$skipped = 0

Write-Host "开始扫描并处理图片..." -ForegroundColor Cyan

foreach ($file in $files) {
    $basename = $file.BaseName
    $extension = $file.Extension
    
    # 3. 检查文件名是否已经包含 _37ac (严格判断是否以 _37ac 结尾)
    if ($basename -notmatch '_37ac$') {
        # 构造新文件名
        $newName = "${basename}_37ac${extension}"
        
        try {
            # 使用 -LiteralPath 避免文件名中的方括号 [] 等特殊字符被当成通配符
            Rename-Item -LiteralPath $file.FullName -NewName $newName -ErrorAction Stop
            Write-Host "已重命名: $($file.Name) -> $newName" -ForegroundColor Green
            $count++
        } catch {
            Write-Host "重命名失败: $($file.Name)。原因: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "跳过 (已包含 _37ac): $($file.Name)" -ForegroundColor Yellow
        $skipped++
    }
}

Write-Host "`n处理完成！" -ForegroundColor Cyan
Write-Host "成功重命名: $count 个文件" -ForegroundColor Green
Write-Host "跳过已存在: $skipped 个文件" -ForegroundColor Yellow