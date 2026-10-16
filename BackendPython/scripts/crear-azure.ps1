#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9]{3,16}$')][string]$Prefix,
    [Parameter(Mandatory)][string]$ResourceGroup,
    [Parameter(Mandatory)][string]$Location,
    [Parameter(Mandatory)][ValidatePattern('\.apps\.googleusercontent\.com$')][string]$GoogleWebClientId
)
$ErrorActionPreference = 'Stop'
if (!(Get-Command az -ErrorAction SilentlyContinue)) { throw 'Instala Azure CLI e inicia sesión con az login.' }
& az account show --output none
if ($LASTEXITCODE -ne 0) { throw 'Ejecuta az login y az account set --subscription TU-SUSCRIPCION.' }
$existing = & az group exists --name $ResourceGroup --output tsv
if ($LASTEXITCODE -ne 0) { throw 'No se pudo consultar el grupo de recursos.' }
if ($existing -eq 'true') { throw 'Usa un grupo de recursos nuevo para esta app. Para recursos existentes consulta la guía.' }

Write-Host 'Creando recursos de Azure: App Service B1, ACR Basic y Cosmos DB serverless. Estos servicios pueden generar cargos.'
& az group create --name $ResourceGroup --location $Location --output none
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el grupo.' }
$randomBytes = [byte[]]::new(48)
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$generator.GetBytes($randomBytes)
$generator.Dispose()
$parameters = @{
    '$schema' = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'
    contentVersion = '1.0.0.0'
    parameters = @{
        prefix = @{ value = $Prefix }
        googleWebClientId = @{ value = $GoogleWebClientId }
        jwtSecret = @{ value = [Convert]::ToBase64String($randomBytes) }
    }
}
$temporaryFile = Join-Path ([IO.Path]::GetTempPath()) ('mensajes-' + [guid]::NewGuid() + '.json')
try {
    $parameters | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $temporaryFile -Encoding utf8
    $result = & az deployment group create --resource-group $ResourceGroup --name mensajes-inicial `
        --template-file (Join-Path $PSScriptRoot '../infra/main.json') --parameters "@$temporaryFile" `
        --query properties.outputs --output json
    if ($LASTEXITCODE -ne 0) { throw 'Azure no pudo completar la creación. Consulta el error de arriba.' }
    $outputs = ($result -join "`n") | ConvertFrom-Json
    Write-Host 'Recursos creados. Configura GitHub con estos valores:'
    Write-Host "AZURE_RESOURCE_GROUP = $ResourceGroup"
    Write-Host "AZURE_WEBAPP_NAME = $($outputs.webAppName.value)"
    Write-Host "ACR_NAME = $($outputs.acrName.value)"
    Write-Host 'AZURE_DEPLOYMENT_MODE = classic'
    Write-Host "URL final = $($outputs.apiUrl.value)"
    Write-Host 'Ahora sigue docs/02-GITHUB-AZURE.md. La API quedará disponible después del primer despliegue.'
} finally {
    if (Test-Path -LiteralPath $temporaryFile) { Remove-Item -LiteralPath $temporaryFile -Force }
    $parameters = $null
    $randomBytes = $null
}
