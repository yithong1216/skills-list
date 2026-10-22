param([Parameter(Mandatory=$true)][string]$InputPath, [Parameter(Mandatory=$true)][string]$PdfPath)
$ErrorActionPreference = 'Stop'
$InputPath = (Resolve-Path -LiteralPath $InputPath).Path
$PdfPath = [System.IO.Path]::GetFullPath($PdfPath)
if ([System.IO.Path]::GetExtension($PdfPath) -ne '.pdf') { throw 'Output must be a PDF path' }
if ($InputPath -eq $PdfPath) { throw 'Input and output must differ' }
New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($PdfPath)) | Out-Null
$pptApp = New-Object -ComObject PowerPoint.Application
$deck = $null
try {
    $deck = $pptApp.Presentations.Open($InputPath, $true, $false, $false)
    $count = $deck.Slides.Count
    $deck.SaveAs($PdfPath, 32)
    if (-not (Test-Path -LiteralPath $PdfPath)) { throw 'PowerPoint did not create the PDF' }
    Write-Output ('PowerPoint opened and rendered ' + $count + ' slides')
} finally {
    if ($null -ne $deck) { $deck.Close() }
    if ($pptApp.Presentations.Count -eq 0) { $pptApp.Quit() }
}
