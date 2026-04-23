/*
 * meh.exe - MIDI Event Handler CLI launcher
 * Compile: gcc -static -O2 -o meh.exe meh.c
 *     or:  cl /O2 /MT meh.c
 * 
 * Console app that hides console when not needed.
 * Uses CreateProcess to avoid spawning intermediate cmd.exe shells.
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

int needs_console(int argc, char *argv[]) {
    for (int i = 1; i < argc; i++) {
        if (_stricmp(argv[i], "debug") == 0)
            return 1;
    }
    return 0;
}

int main(int argc, char *argv[]) {
    int is_debug = needs_console(argc, argv);
    
    // Get our console window
    HWND consoleWnd = GetConsoleWindow();
    DWORD consolePid = 0;
    
    if (consoleWnd) {
        GetWindowThreadProcessId(consoleWnd, &consolePid);
    }
    
    // If we own the console (launched from Explorer) and don't need it, hide it
    int own_console = (consolePid == GetCurrentProcessId());
    if (own_console && !is_debug) {
        FreeConsole();
    }

    // Get directory where this exe lives
    char exePath[MAX_PATH];
    GetModuleFileNameA(NULL, exePath, MAX_PATH);
    char *lastSlash = strrchr(exePath, '\\');
    if (lastSlash) *lastSlash = '\0';

    // Build python executable path
    char pythonExe[MAX_PATH];
    sprintf(pythonExe, "%s\\python\\python.exe", exePath);

    // Build command line
    char cmd[8192];
    char *p = cmd;
    p += sprintf(p, "\"%s\" -m midi_event_handler.launcher", pythonExe);
    
    // If running from terminal (not our own console), pass --console flag
    if (!own_console) {
        p += sprintf(p, " --console");
    }
    
    for (int i = 1; i < argc; i++) {
        if (strchr(argv[i], ' '))
            p += sprintf(p, " \"%s\"", argv[i]);
        else
            p += sprintf(p, " %s", argv[i]);
    }

    // Launch Python
    STARTUPINFOA si = {0};
    PROCESS_INFORMATION pi = {0};
    si.cb = sizeof(si);
    
    // If no console, create process with no window
    DWORD flags = (own_console && !is_debug) ? CREATE_NO_WINDOW : 0;
    
    BOOL success = CreateProcessA(
        pythonExe,
        cmd,
        NULL, NULL,
        FALSE,
        flags,
        NULL,
        exePath,
        &si, &pi
    );

    DWORD exitCode = 1;
    if (success) {
        WaitForSingleObject(pi.hProcess, INFINITE);
        GetExitCodeProcess(pi.hProcess, &exitCode);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }

    // If we created our own console for debug, wait before closing
    if (own_console && is_debug) {
        printf("\nPress Enter to exit...");
        getchar();
    }

    return (int)exitCode;
}
