@echo off
title Cod-Chlo Continuous Video Automation
cd /d %~dp0
echo [*] Starting Cod-Chlo Runner Forever...
python runner_forever.py --interval 86400
pause
