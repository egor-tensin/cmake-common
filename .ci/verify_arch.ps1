param(
    [Parameter(Mandatory=$true)]
    [string] $Path,
    [Parameter(Mandatory=$true)]
    [ValidateSet('x64', 'x86')]
    [string] $Arch
)

$ErrorActionPreference = "Stop";
Set-PSDebug -Strict

function Get-MachineType {
    param(
        [Parameter(Mandatory=$true)]
        [string] $Arch
    )

    $machine_type = switch ($Arch) {
        'x64' { 0x8664 }
        'x86' { 0x14c }
        default { throw "Unsupported architecture: $Arch" }
    }
    return $machine_type
}

function Parse-MachineType {
    param(
        [Parameter(Mandatory=$true)]
        [string] $Path
    )

    $header_offset_offset = 0x3c
    $machine_type_offset = 4 # Two words

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $header_offset = [System.BitConverter]::ToUInt32($bytes, $header_offset_offset)
    $machine_type = [System.BitConverter]::ToUInt16($bytes, $header_offset + $machine_type_offset)

    return $machine_type
}

function Verify-Architecture {
    param(
        [Parameter(Mandatory=$true)]
        [string] $Path,
        [Parameter(Mandatory=$true)]
        [string] $Arch
    )

    $actual = Parse-MachineType -Path $Path
    $actual_hex = "0x{0:x}" -f $actual
    $expected = Get-MachineType -Arch $Arch
    $expected_hex = "0x{0:x}" -f $expected

    if ($actual -eq $expected) {
        Write-Host "File '$Path' matches architecture '$Arch'."
    } else {
        Write-Host "File '$Path' DOES NOT match architecture '$Arch'."
        Write-Error "Expected machine type '$expected_hex', actual machine type is '$actual_hex'."
    }
}

function Test-AppVeyor {
    return Test-Path env:APPVEYOR
}

function Verify-ArchitectureAppVeyor {
    if (Test-AppVeyor) {
        $appveyor_cwd = pwd
    }

    try {
        Verify-Architecture -Path $script:Path -Arch $script:Arch
    } finally {
        if (Test-AppVeyor) {
            cd $appveyor_cwd
            Set-PSDebug -Off
        }
    }
}

Verify-ArchitectureAppVeyor
