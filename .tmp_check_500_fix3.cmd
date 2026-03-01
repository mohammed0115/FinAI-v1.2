@echo off
cd /d "C:\Users\jnass\NodeJs Projects\FinAI-v1.2"
if exist "frontend-next\dev.log" del /f /q "frontend-next\dev.log"
start /b npx next dev frontend-next --webpack --port 3018 > "frontend-next\dev.log" 2>&1
timeout /t 9 >nul
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://localhost:3018/ar/login' -UseBasicParsing -TimeoutSec 20; Write-Output ('STATUS=' + [int]$r.StatusCode) } catch { if($_.Exception.Response){ $resp=$_.Exception.Response; Write-Output ('STATUS=' + [int]$resp.StatusCode.value__); } else { Write-Output $_.Exception.Message } }"
timeout /t 2 >nul
type "frontend-next\dev.log"
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r /c:":3018 .*LISTENING"') do taskkill /PID %%a /F >nul 2>&1
