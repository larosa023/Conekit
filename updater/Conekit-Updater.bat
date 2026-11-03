@echo off
:: Conekit installer / updater - double-click to install, update, or switch Dark/Light.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Conekit-Updater.ps1" %*
