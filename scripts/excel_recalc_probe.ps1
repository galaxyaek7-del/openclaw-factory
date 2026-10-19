# Galaxy Forge — native spreadsheet recalculation probe.
#
# Opens a temporary read-only copy of a workbook in the installed Microsoft
# Excel via COM, forces a full recalculation, and dumps what Excel actually
# displays. It makes no judgement about correctness; native_workbook_qa.py
# decides pass/fail so the rules stay testable without Excel installed.
#
# Usage:
#   powershell -NoProfile -File scripts/excel_recalc_probe.ps1 -Spec <spec.json> -Out <out.json>
#
# Spec (JSON):
#   {
#     "artifact": "books/batch12/<name>.xlsx",
#     "formula_sheets": ["Opportunities", "Timeline", "Dashboard"],
#     "scan_sheets": ["Dashboard", "Opportunities"],   # optional; default = all sheets
#     "cells": [ {"sheet": "Dashboard", "address": "B6"} ]   # optional explicit cells
#   }
#
# The canonical workbook is never opened for write. The copy is closed without
# saving and deleted, so a probe run cannot mutate a release artifact.

param(
    [Parameter(Mandatory = $true)][string]$Spec,
    [Parameter(Mandatory = $true)][string]$Out,
    [string]$Root = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

$specData = Get-Content -LiteralPath $Spec -Raw | ConvertFrom-Json
$artifact = Join-Path $Root $specData.artifact
if (-not (Test-Path -LiteralPath $artifact)) {
    throw "artifact not found: $artifact"
}

$tmp = Join-Path $env:TEMP ("gf_recalc_probe_" + [guid]::NewGuid().ToString("N") + ".xlsx")
Copy-Item -LiteralPath $artifact -Destination $tmp -Force

$excel = $null
$wb = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.ScreenUpdating = $false

    $wb = $excel.Workbooks.Open($tmp, 0, $true)
    # Calculation mode can only be set after the workbook is open (0x800A03EC otherwise).
    $excel.Calculation = -4105
    $wb.Application.CalculateFullRebuild() | Out-Null
    $excel.Calculate() | Out-Null

    $errorLiterals = @("#VALUE!", "#DIV/0!", "#REF!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "Err:502", "Err:508", "Err:509", "Err:522")

    $scanNames = @()
    if ($specData.scan_sheets) { $scanNames = @($specData.scan_sheets) } else { foreach ($ws in $wb.Worksheets) { $scanNames += $ws.Name } }

    $cellsOut = New-Object System.Collections.ArrayList
    $errorsOut = New-Object System.Collections.ArrayList
    
    foreach ($ws in $wb.Worksheets) {
        foreach ($cell in $ws.UsedRange.Cells) {
            $text = $cell.Text
            if ($text -isnot [string]) { continue }
            $trimmed = $text.Trim()
            if ($errorLiterals -contains $trimmed) {
                [void]$errorsOut.Add([pscustomobject]@{ sheet = $ws.Name; address = [string]$cell.Address($false, $false); text = $trimmed })
            }
        }
    }

    foreach ($name in $scanNames) {
        $ws = $wb.Worksheets.Item($name)
        if ($null -eq $ws) { continue }
        foreach ($cell in $ws.UsedRange.Cells) {
            $text = $cell.Text
            $formula = $null
            if ($cell.HasFormula) { $formula = [string]$cell.Formula }
            $value = $cell.Value2
            $hasText = ($text -is [string]) -and ($text.Trim() -ne "")
            $hasValue = ($null -ne $value)
            if (-not $hasText -and -not $hasValue -and -not $formula) { continue }
            [void]$cellsOut.Add([pscustomobject]@{
                sheet   = $name
                address = [string]$cell.Address($false, $false)
                row     = [int]$cell.Row
                column  = [int]$cell.Column
                text    = if ($text -is [string]) { [string]$text } else { "" }
                value   = $value
                format  = [string]$cell.NumberFormat
                formula = $formula
            })
        }
    }

    $formulaCount = 0
    foreach ($name in @($specData.formula_sheets)) {
        if (-not $name) { continue }
        $ws = $wb.Worksheets.Item($name)
        $special = $ws.UsedRange.SpecialCells(2)
        if ($null -ne $special) { $formulaCount += [int]$special.Count }
    }

    $artifactInfo = Get-Item -LiteralPath $artifact
    $hash = (Get-FileHash -LiteralPath $artifact -Algorithm SHA256).Hash.ToLower()

    $result = [pscustomobject]@{
        schema                 = "native_recalc_probe/v1"
        engine                 = [pscustomobject]@{ name = "Microsoft Excel"; version = [string]$excel.Version; build = [string]$excel.Build }
        artifact               = $specData.artifact
        artifact_bytes         = [int]$artifactInfo.Length
        artifact_sha256        = $hash
        calculated_at_utc      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        method                 = "Temporary read-only copy opened by COM automation; CalculateFullRebuild() then read. Copy closed without saving and deleted. The canonical file was never opened for write."
        formula_cells          = $formulaCount
        formula_sheets         = @($specData.formula_sheets)
        scanned_sheets         = $scanNames
        error_cells            = @($errorsOut)
        cells                  = @($cellsOut)
    }

    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Out -Encoding UTF8
}
finally {
    if ($wb) { $wb.Close($false) | Out-Null }
    if ($excel) { $excel.Quit() }
    [System.GC]::Collect() | Out-Null
    [System.GC]::WaitForPendingFinalizers() | Out-Null
    if ($wb) { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($wb) }
    if ($excel) { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) }
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

Write-Output "PROBE_OK"
