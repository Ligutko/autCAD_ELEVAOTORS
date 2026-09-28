# Render scenes one after another while keeping Windows awake (the PC sleeps during long renders and a
# frame then "runs" for hours). Asks for ES_SYSTEM_REQUIRED only while this script runs; no power
# settings are changed.
#   powershell -File world/build/render_awake.ps1 -Scenes k1_silo,k5_interior,site [-Quick] [-Extra "--night"]
param([string[]]$Scenes, [switch]$Quick, [string]$Extra = "")
Add-Type -Namespace Win -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[void][Win.Power]::SetThreadExecutionState([uint32]"0x80000001")   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
$B = if ($env:BLENDER) { $env:BLENDER } else { "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" }
Set-Location (Split-Path (Split-Path $PSScriptRoot))
try {
    foreach ($s in $Scenes) {
        "== $s $(Get-Date -Format HH:mm)"
        $extra = @()
        if ($Quick) { $extra += "--quick" }
        if ($Extra) { $extra += ($Extra -split " ") }
        if ($extra.Count) { $extra = @("--") + $extra }
        & $B --background --python "world/build/$s.py" @extra 2>&1 | ForEach-Object { "$_" } | Where-Object { $_ -match "^rendered|Error|Traceback" }
    }
} finally {
    [void][Win.Power]::SetThreadExecutionState([uint32]"0x80000000")
}
"done $(Get-Date -Format HH:mm)"
