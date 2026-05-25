# YaLoader

YaLoader is a modern Windows desktop application for downloading video and audio using yt-dlp and FFmpeg.

## User setup

YaLoader uses yt-dlp to download media. For YouTube, some videos may require:

- FFmpeg for merging video and audio streams
- Deno for JavaScript challenge solving
- yt-dlp for downloading media
- cookies.txt for authenticated YouTube access

### 1. Install FFmpeg

Install FFmpeg and make sure it is available in PATH.

```powershell
winget install -e --id Gyan.FFmpeg
```

If the command works, FFmpeg is available.

### 2. Install Deno

Install Deno:

```powershell
winget install DenoLand.Deno
```

Close and reopen the terminal, then check:

```powershell
deno --version
```

Deno is used by yt-dlp for YouTube JavaScript challenge solving.

### 3. Install yt-dlp

Install yt-dlp:

```powershell
winget install -e --id yt-dlp.yt-dlp
```

### 4. Prepare cookies.txt

YaLoader automatically looks for cookies here:

```text
%APPDATA%\yaloader\cookies.txt
```

Usually this expands to:

```text
C:\Users\<UserName>\AppData\Roaming\yaloader\cookies.txt
```

Create the folder if it does not exist:

```powershell
mkdir "$env:APPDATA\yaloader" -Force
```

Download Mozilla.Firefox if you don't have it:

```powershell
winget install Mozilla.Firefox
```

Log in to YouTube in Firefox, then export cookies from Firefox:

```powershell
yt-dlp --cookies-from-browser firefox --cookies "$env:APPDATA\yaloader\cookies.txt"
```

### You can also use a browser extension or other methods to export cookies, but using yt-dlp is more straightforward and ensures the correct format.

The generated file must start with something like:

```text
# Netscape HTTP Cookie File
```

# DO NOT SHARE `cookies.txt` WITH ANYONE. It may contain active Google or YouTube session cookies.