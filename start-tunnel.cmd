@echo off
set LOGFILE=%USERPROFILE%\Desktop\sentinelrag-url.txt
set TUNNELLOG=%TEMP%\cloudflared.log

echo Starting SentinelRAG Tunnel... > "%LOGFILE%"
echo %date% %time% >> "%LOGFILE%"

"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:80 > "%TUNNELLOG%" 2>&1
