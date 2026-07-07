@echo off
REM Windows için UTF-8 zorlamalı Python çalıştırıcı
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python -m src.agents.tools.sql_executor
