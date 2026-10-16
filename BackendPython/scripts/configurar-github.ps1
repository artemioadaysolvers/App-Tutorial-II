#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')][string]$Repository,
    [Parameter(Mandatory)][string]$ResourceGroup,
    [Parameter(Mandatory)][string]$AcrName,
    [Parameter(Mandatory)][string]$WebAppName
)
$ErrorActionPreference = 'Stop'
function Invoke-AzureJson([string[]]$Arguments) {
    $lines = & az @Arguments --only-show-errors --output json
    if ($LASTEXITCODE -ne 0) { throw "Azure CLI falló: $($Arguments[0]) $($Arguments[1])" }
    return ($lines -join "`n") | ConvertFrom-Json
}
if (!(Get-Command az -ErrorAction SilentlyContinue)) { throw 'Instala Azure CLI.' }
$account = Invoke-AzureJson -Arguments @('account', 'show')
$registry = Invoke-AzureJson -Arguments @('acr', 'show', '--resource-group', $ResourceGroup, '--name', $AcrName)
$web = Invoke-AzureJson -Arguments @('webapp', 'show', '--resource-group', $ResourceGroup, '--name', $WebAppName)
$application = Invoke-AzureJson -Arguments @('ad', 'app', 'create', '--display-name', "mensajes-github-$([guid]::NewGuid().ToString('N').Substring(0,8))")
$principal = Invoke-AzureJson -Arguments @('ad', 'sp', 'create', '--id', $application.appId)
$federation = @{
    name = 'github-main'
    issuer = 'https://token.actions.githubusercontent.com'
    subject = "repo:${Repository}:ref:refs/heads/main"
    description = 'Actualizar backend Mensajes desde main'
    audiences = @('api://AzureADTokenExchange')
}
$temporaryFile = Join-Path ([IO.Path]::GetTempPath()) ('mensajes-oidc-' + [guid]::NewGuid() + '.json')
try {
    $federation | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporaryFile -Encoding utf8
    $null = Invoke-AzureJson -Arguments @('ad', 'app', 'federated-credential', 'create', '--id', $application.id, '--parameters', $temporaryFile)
    $null = Invoke-AzureJson -Arguments @('role', 'assignment', 'create', '--assignee-object-id', $principal.id, '--assignee-principal-type', 'ServicePrincipal', '--role', 'AcrPush', '--scope', $registry.id)
    $null = Invoke-AzureJson -Arguments @('role', 'assignment', 'create', '--assignee-object-id', $principal.id, '--assignee-principal-type', 'ServicePrincipal', '--role', 'Website Contributor', '--scope', $web.id)
} finally {
    if (Test-Path -LiteralPath $temporaryFile) { Remove-Item -LiteralPath $temporaryFile -Force }
}
Write-Host "En https://github.com/$Repository/settings/secrets/actions crea estos tres secretos:"
Write-Host "AZURE_CLIENT_ID = $($application.appId)"
Write-Host "AZURE_TENANT_ID = $($account.tenantId)"
Write-Host "AZURE_SUBSCRIPTION_ID = $($account.id)"
Write-Host 'En la pestaña Variables crea:'
Write-Host "AZURE_RESOURCE_GROUP = $ResourceGroup"
Write-Host "AZURE_WEBAPP_NAME = $WebAppName"
Write-Host "ACR_NAME = $AcrName"
Write-Host 'AZURE_DEPLOYMENT_MODE = classic (o sidecar si tu App Service usa sitecontainers)'
Write-Host 'No se generó contraseña de Azure: se utiliza la identidad federada de GitHub.'
