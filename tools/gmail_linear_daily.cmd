@echo off
setlocal
set "PROJDIR=C:\GitHub\claude-template-session"
set "CLAUDEEXE=C:\Users\Dell\.local\bin\claude.exe"
set "LOGDIR=%PROJDIR%\tools\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
cd /d "%PROJDIR%"
echo ==== Run started %DATE% %TIME% ==== >> "%LOGDIR%\gmail_linear_daily.log"
"%CLAUDEEXE%" -p "/gmail-linear-exports Scan the Gmail inbox for the last 24 hours using the Gmail query newer_than:1d in:inbox, then export each candidate email or action point to the Linear team named Grok Build. This is an unattended scheduled run with no human present, so do NOT ask for any confirmation and do NOT wait for input; the target team is already decided as Grok Build. Anonymize strictly per the skill hard rule: no personal names, email addresses, or company identifiers anywhere in the digest or in Linear. Skip pure newsletters and automated mail that carry no action. Create the Linear issues directly with sensible priorities, then print a compact summary of the issues created." --model claude-sonnet-5 --allowedTools "mcp__linear mcp__claude_ai_Gmail Skill Read TodoWrite" >> "%LOGDIR%\gmail_linear_daily.log" 2>&1
echo ==== Run finished %DATE% %TIME% exit %ERRORLEVEL% ==== >> "%LOGDIR%\gmail_linear_daily.log"
endlocal
