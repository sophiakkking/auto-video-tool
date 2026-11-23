@echo off
rem 开发用 PostgreSQL 启停（免安装绿色版，无管理员权限）
rem 用法: dev-db.cmd start | stop | status
setlocal
set PGBIN=C:\Users\Morefun\tools\pgsql\bin
set PGDATA=C:\Users\Morefun\tools\pgsql\data
set PGLOG=C:\Users\Morefun\tools\pgsql\pg.log

if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="status" goto status
echo 用法: dev-db.cmd start ^| stop ^| status
goto :eof

:start
"%PGBIN%\pg_ctl.exe" -D "%PGDATA%" -l "%PGLOG%" start
goto :eof

:stop
"%PGBIN%\pg_ctl.exe" -D "%PGDATA%" stop
goto :eof

:status
"%PGBIN%\pg_ctl.exe" -D "%PGDATA%" status
goto :eof
