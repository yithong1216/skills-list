param([Parameter(Mandatory=$true)][string]$InputDir,
      [Parameter(Mandatory=$true)][string]$OutputDir,
      [string]$Language = 'zh-Hans-CN')
$ErrorActionPreference = 'Stop'
$InputDir = (Resolve-Path -LiteralPath $InputDir).Path
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function AwaitOperation($operation, $resultType) {
    $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait()
    return $task.Result
}
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new($Language))
if ($null -eq $engine) {
    $available = [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object { $_.LanguageTag }
    throw "Local OCR language '$Language' is not installed. Available: $($available -join ', ')"
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
foreach ($page in Get-ChildItem -LiteralPath $InputDir -Directory | Sort-Object Name) {
    if (-not (Test-Path -LiteralPath (Join-Path $page.FullName 'source.png'))) { continue }
    $file = AwaitOperation ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Join-Path $page.FullName 'source.png'))) ([Windows.Storage.StorageFile])
    $stream = AwaitOperation ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = AwaitOperation ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = AwaitOperation ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    if ($bitmap.PixelWidth -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension -or $bitmap.PixelHeight -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension) {
        $bitmap.Dispose()
        $stream.Dispose()
        throw "Image exceeds Windows OCR limit on $($page.Name). Make a smaller OCR-only copy and record its coordinate scale; retain the original source."
    }
    $result = AwaitOperation ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $lines = @($result.Lines | ForEach-Object { @{ text=$_.Text; words=@($_.Words | ForEach-Object { @{text=$_.Text; box=@($_.BoundingRect.X,$_.BoundingRect.Y,$_.BoundingRect.Width,$_.BoundingRect.Height)} }) } })
    @{backend='Windows.Media.Ocr'; local_only=$true; language=$Language; source=(Join-Path $page.FullName 'source.png'); width_px=$bitmap.PixelWidth; height_px=$bitmap.PixelHeight; lines=$lines} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputDir ($page.Name+'.json')) -Encoding UTF8
    $bitmap.Dispose()
    $stream.Dispose()
    Write-Output ($page.Name + ': ' + $lines.Count + ' lines')
}
