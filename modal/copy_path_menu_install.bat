@echo off
:: Run as Administrator
powershell -Command "Start-Process pwsh -ArgumentList '-File', '%~dp0copy_path_menu.ps1' -Verb RunAs"
