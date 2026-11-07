# Startup and hands-free sign-in

Gwen is registered in the current user's Windows Startup folder. After Windows signs this user in, the shortcut starts the resident background assistant and cursor marker using this installation's virtual environment. The working directory and script paths are absolute and support spaces. The existing single-instance guard prevents a second resident process. Offline voice restores the last listening mode when enabled in `voice_config.json`; **Gwen listen** stays enabled until **Gwen sleep** or voice off. The panel starts hidden by default; **Gwen show chat** or F10 restores it explicitly. See [OFFLINE_VOICE.md](OFFLINE_VOICE.md).

## Manage automatic startup

From this project folder:

```powershell
.\.venv\Scripts\python.exe startup.py status
.\.venv\Scripts\python.exe startup.py enable
.\.venv\Scripts\python.exe startup.py disable
```

The shortcut is `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Gwen Doer.lnk`. Disabling removes only the shortcut created by this module; it leaves Gwen and all project files installed. Moving the project or replacing its virtual environment requires enabling startup again from its new location. Windows can delay Startup items or disable them through Startup Apps; this is not a system service or a pre-logon launch.

## Before Windows sign-in

The password/PIN screen is a protected Windows desktop. The current unsigned Python GUI, its mouse/keyboard input and its future ordinary voice listener do not run there just because a startup shortcut exists. Running a script as a normal user, adding a boot trigger, or adding an ordinary service does not by itself provide interactive logon-screen control.

Windows 11 Voice Access provides a supported hands-free route for sign-in. In **Settings > Accessibility > Speech > Voice access**, complete the microphone/language setup and enable **Start voice access before you sign in to your PC**. Microsoft documents using it to focus the password/PIN field and dictate credentials, including the on-screen keyboard and numbered labels. Its capabilities and language availability depend on the installed Windows build and speech pack. This setup is performed by the user; Gwen's startup installation does not configure a microphone, save credentials, enable automatic login, or change sign-in settings.

The intended combined flow is:

1. Windows starts and reaches its sign-in screen.
2. Windows Voice Access handles supported sign-in interactions using the user's spoken commands.
3. After successful sign-in, Windows starts Gwen automatically.
4. Gwen handles desktop apps, grids and agent commands using its offline voice module.

Microsoft's guide: https://support.microsoft.com/en-gb/accessibility/windows/voice-access/use-voice-access-to-set-up-and-log-in-to-your-pc

## Future Gwen-owned logon integration

A custom pre-sign-in Gwen component is a separate accessibility deployment project. It needs evaluation of Microsoft's trusted UIAccess packaging requirements (Authenticode signing, protected installation location and an appropriate manifest) and Ease of Access assistive-technology registration/secure-desktop behavior. UIAccess alone is not an automatic logon-screen implementation. The current Desktop Python installation does not implement that component. Password/PIN input must stay outside planner prompts, screenshots retained for diagnostics, speech transcripts and ordinary application logs.

Microsoft references:

- https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-securityoverview
- https://learn.microsoft.com/en-us/windows/win32/winauto/ease-of-access---assistive-technology-registration

Verification here checks the shortcut target, arguments and working directory and launches the same shortcut into the existing single-instance runtime. No reboot, sign-out, lock-screen interaction or password entry is performed during development verification.
