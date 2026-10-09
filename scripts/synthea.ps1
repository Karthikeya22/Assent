# Generate the Synthea background population (Medicare-age, seeded) into .data/synthea/fhir.
# Usage: .\scripts\synthea.ps1 [-Count 80] [-Seed 7]
param([int]$Count = 80, [int]$Seed = 7)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $root '.data\synthea'
New-Item -ItemType Directory -Force $out | Out-Null

& 'D:\DevTools\jdk17\Library\bin\java.exe' -Xmx1g "-Djava.io.tmpdir=D:\.tmp" `
  -jar 'D:\DevTools\synthea\synthea-with-dependencies.jar' `
  -p $Count -s $Seed -cs $Seed -a 65-90 `
  --exporter.baseDirectory "$out" `
  --exporter.years_of_history 5 `
  --exporter.fhir.export true `
  --exporter.fhir.transaction_bundle true `
  --exporter.hospital.fhir.export false `
  --exporter.practitioner.fhir.export false `
  --exporter.csv.export false `
  --generate.only_alive_patients true `
  Massachusetts
