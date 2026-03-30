param(
    [Parameter(Mandatory=$true)]
    [string] $FooPath
)

$foo_path = [System.IO.Path]::GetFullPath($FooPath)
if ($IsWindows) {
    $foo_path += '.exe'
}

$relative = 'test.txt'
$absolute = Join-Path (Get-Location).Path $relative

$actual = & $foo_path $relative
echo 'Actual output:'
echo $actual

$expected = $foo_path,$absolute
echo 'Expected output:'
echo $expected

if (Compare-Object $actual $expected -CaseSensitive) {
    throw 'Unexpected output'
}
