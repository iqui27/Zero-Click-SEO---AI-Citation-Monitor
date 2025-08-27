# Script PowerShell para testar conectividade com Azure SQL Database
# Execute: .\scripts\test-database.ps1

Write-Host "🚀 Teste de Conectividade Azure SQL Database" -ForegroundColor Green
Write-Host "=" * 50

# Verificar se DATABASE_URL está definida
$databaseUrl = $env:DATABASE_URL

if (-not $databaseUrl) {
    Write-Host "❌ DATABASE_URL não encontrada nas variáveis de ambiente" -ForegroundColor Red
    Write-Host "💡 Defina a variável primeiro:" -ForegroundColor Yellow
    Write-Host "   `$env:DATABASE_URL = 'sua_string_de_conexao'" -ForegroundColor Cyan
    
    # Tentar carregar do .env se existir
    if (Test-Path ".env") {
        Write-Host "📁 Tentando carregar do arquivo .env..." -ForegroundColor Yellow
        
        $envContent = Get-Content ".env" | Where-Object { $_ -match "^DATABASE_URL=" }
        if ($envContent) {
            $databaseUrl = ($envContent -split "=", 2)[1].Trim('"')
            Write-Host "✅ DATABASE_URL carregada do .env" -ForegroundColor Green
        }
    }
    
    if (-not $databaseUrl) {
        Write-Host "❌ DATABASE_URL não encontrada em lugar nenhum" -ForegroundColor Red
        exit 1
    }
}

Write-Host "🔍 Testando conectividade..." -ForegroundColor Cyan
Write-Host "📋 DATABASE_URL encontrada (primeiros 50 chars): $($databaseUrl.Substring(0, [Math]::Min(50, $databaseUrl.Length)))..." -ForegroundColor Gray

# Parse da URL para extrair informações
try {
    $uri = [System.Uri]$databaseUrl.Replace("mssql+pyodbc://", "http://")
    
    $server = $uri.Host
    $port = if ($uri.Port -eq -1) { 1433 } else { $uri.Port }
    $database = $uri.AbsolutePath.TrimStart('/')
    $username = $uri.UserInfo.Split(':')[0]
    
    Write-Host "🎯 Servidor: $server" -ForegroundColor White
    Write-Host "🔌 Porta: $port" -ForegroundColor White
    Write-Host "🗄️  Database: $database" -ForegroundColor White
    Write-Host "👤 Usuário: $username" -ForegroundColor White
    
} catch {
    Write-Host "❌ Erro ao fazer parse da DATABASE_URL: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Testar conectividade TCP
Write-Host "`n🔌 Testando conectividade TCP..." -ForegroundColor Cyan

try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $asyncResult = $tcpClient.BeginConnect($server, $port, $null, $null)
    $wait = $asyncResult.AsyncWaitHandle.WaitOne(10000, $false)
    
    if ($wait) {
        try {
            $tcpClient.EndConnect($asyncResult)
            Write-Host "✅ Conectividade TCP: OK" -ForegroundColor Green
            $tcpClient.Close()
        } catch {
            Write-Host "❌ Conectividade TCP: FALHOU" -ForegroundColor Red
            Write-Host "   Erro: $($_.Exception.Message)" -ForegroundColor Gray
            Write-Host "   Possíveis causas:" -ForegroundColor Yellow
            Write-Host "   - Firewall do Azure SQL bloqueando este IP" -ForegroundColor Gray
            Write-Host "   - Problema de rede/DNS" -ForegroundColor Gray
            $tcpClient.Close()
            exit 1
        }
    } else {
        Write-Host "❌ Conectividade TCP: TIMEOUT" -ForegroundColor Red
        Write-Host "   Servidor não respondeu em 10 segundos" -ForegroundColor Gray
        $tcpClient.Close()
        exit 1
    }
} catch {
    Write-Host "❌ Erro no teste TCP: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Testar resolução DNS
Write-Host "`n🌐 Testando resolução DNS..." -ForegroundColor Cyan
try {
    $dnsResult = Resolve-DnsName -Name $server -ErrorAction Stop
    Write-Host "✅ Resolução DNS: OK" -ForegroundColor Green
    Write-Host "   IP resolvido: $($dnsResult[0].IPAddress)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Resolução DNS: FALHOU" -ForegroundColor Red
    Write-Host "   Erro: $($_.Exception.Message)" -ForegroundColor Gray
}

# Testar conexão SQL (se SqlServer module estiver disponível)
Write-Host "`n🗄️  Testando conexão SQL..." -ForegroundColor Cyan

# Verificar se módulo SqlServer está disponível
$sqlModuleAvailable = Get-Module -ListAvailable -Name SqlServer

if ($sqlModuleAvailable) {
    try {
        Import-Module SqlServer -ErrorAction Stop
        
        # Construir connection string
        $connectionString = $databaseUrl
        
        Write-Host "⏳ Tentando conectar ao banco de dados..." -ForegroundColor Yellow
        
        $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
        $connection.ConnectionTimeout = 30
        $connection.Open()
        
        Write-Host "✅ Conexão SQL: OK" -ForegroundColor Green
        
        # Testar query simples
        $command = $connection.CreateCommand()
        $command.CommandText = "SELECT 1 as test"
        $result = $command.ExecuteScalar()
        
        if ($result -eq 1) {
            Write-Host "✅ Query de teste: OK" -ForegroundColor Green
        }
        
        $connection.Close()
        Write-Host "🎉 Teste de conectividade: SUCESSO!" -ForegroundColor Green
        
    } catch {
        Write-Host "❌ Erro na conexão SQL: $($_.Exception.Message)" -ForegroundColor Red
        
        $errorMsg = $_.Exception.Message.ToLower()
        
        if ($errorMsg -match "timeout") {
            Write-Host "💡 Erro de timeout - verifique firewall do Azure SQL" -ForegroundColor Yellow
        } elseif ($errorMsg -match "login failed") {
            Write-Host "💡 Erro de login - verifique usuário/senha" -ForegroundColor Yellow
        } elseif ($errorMsg -match "cannot open database") {
            Write-Host "💡 Erro de database - verifique nome do banco" -ForegroundColor Yellow
        } elseif ($errorMsg -match "ssl") {
            Write-Host "💡 Erro SSL - verifique configuração de certificados" -ForegroundColor Yellow
        }
        
        exit 1
    }
} else {
    Write-Host "⚠️  Módulo SqlServer não disponível - teste SQL pulado" -ForegroundColor Yellow
    Write-Host "   Instale com: Install-Module -Name SqlServer" -ForegroundColor Gray
}

Write-Host "`n✅ Teste concluído!" -ForegroundColor Green
