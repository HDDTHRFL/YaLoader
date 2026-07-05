# YaLoader

YaLoader is a Windows desktop application that helps download video and audio from YouTube and other platforms supported by yt-dlp.

The main workflow is handled directly in the app interface. Add a link to the queue, choose the format and quality, and the app will check the required download components and download the selected files.

## Release archive contents

The release archive is intentionally portable and minimal. It contains:

- `YaLoader.exe`;
- `README.md`;
- `README_RU.md`;
- `LICENSE`;
- `SHA256SUMS.txt`.

Release archives do not include local settings, logs, downloaded files, browser cookies, or developer-only documentation.

## Features

YaLoader can:

- download video;
- download audio;
- select video quality;
- select output format;
- download YouTube Shorts;
- work with playlists;
- add multiple links to a queue;
- limit download speed;
- cancel downloads;
- show download history;
- open the folder with the downloaded file;
- use `cookies.txt` for content that requires account access;
- check whether the required download tools are available.

## Supported sources

YaLoader relies on `yt-dlp`, so the exact list of supported websites depends on the current yt-dlp runtime and on changes made by the platforms themselves.

The application is focused on normal desktop use and currently includes platform detection for popular sources such as YouTube, Rutube, VK, Twitch, and SoundCloud when metadata is available.

## Installation

1. Download the latest YaLoader version from the project releases page.
2. Run `YaLoader.exe`.
3. On first launch, check the “System status” block.
4. If the application says that FFmpeg or Deno is missing, click “Prepare system”.
5. Choose a downloads folder if the default folder does not suit you.

Windows may show a SmartScreen warning because the application may not be signed with a digital certificate. Run the application only if you downloaded it from a trusted source.

## Updating

Use the latest archive from the GitHub Releases page. For a manual update, close YaLoader, replace the old application files with the files from the new archive, and start `YaLoader.exe` again.

If the built-in update check is used, the application expects the official Windows x64 release archive name and checksum published with the release.

## Initial `cookies.txt` setup

For regular public videos, `cookies.txt` is usually not required.

Cookies may be needed if YouTube or another service asks you to confirm your account, restricts access to a video, shows an “are you a bot” check, or does not provide some formats.

In YaLoader, you can add `cookies.txt` through the application interface. The most stable option is extracting cookies from Firefox or Opera. Extraction from Chrome, Edge, and some other browsers may fail because of browser restrictions, a locked cookies database, or yt-dlp behavior.

If cookies extraction fails:

1. Fully close the browser.
2. Make sure it is not still running in the system tray or background processes.
3. Try again.
4. If the error repeats, use Firefox or Opera.

## Never send your `cookies.txt` to anyone

The `cookies.txt` file may contain active browser session data. If you send it to another person, they may potentially gain access to your accounts or perform actions on your behalf.

Any transfer, storage, or use of `cookies.txt` outside YaLoader is done at your own risk.

## How to use

1. Copy a link to a video, Shorts, or playlist.
2. Paste the link into the YaLoader input field.
3. Select the download mode: video or audio.
4. Select format and quality.
5. Click “Add to queue”, then start the download.
6. Wait for the download to finish.
7. Open the file from history or from the downloads folder.

If the link points to a YouTube playlist, the application may process it as a playlist without a separate toggle.

## Troubleshooting

### YouTube asks you to confirm that you are not a bot

Add an up-to-date `cookies.txt` from a browser where you are signed in to YouTube. Firefox or Opera is recommended.

### `cookies.txt` cannot be created from Chrome, Edge, or another browser

Fully close the browser and try again. If that does not help, use Firefox or Opera. These browsers are usually more stable for cookies extraction through yt-dlp.

### The video does not download, or the application says that the format is unavailable

Try the following:

- update tools through the application;
- add an up-to-date `cookies.txt`;
- select another quality;
- select another format;
- try again later.

Sometimes YouTube temporarily changes available formats or restricts access to individual videos.

### FFmpeg or Deno is missing

In the “System status” block, click “Prepare system”. The application will try to install the required portable tools.

### The file did not appear in the downloads folder

Check the download history and the selected downloads folder. Also make sure that antivirus software or Windows SmartScreen did not block the application.

### Download speed is too slow

Check the speed limit in the application settings. If the limit is enabled, disable it or choose a higher value.

## Release checksums

Each release archive contains `SHA256SUMS.txt`. The release packaging step also creates an external `.sha256` file next to the archive.

Use the SHA-256 checksum from the GitHub Release description or from the `.sha256` file if you need to verify that the downloaded archive was not corrupted.

## License

The project is distributed as source-available software for personal, educational, evaluation, and other non-commercial use.

The following are prohibited without prior written permission:

- commercial use;
- sale;
- sublicensing;
- publication of modified versions;
- distribution of modified builds;
- removal of copyright notice or license notice.

Full terms are provided in the `LICENSE` file.

## For developers

Technical information, architecture, check commands, and development rules are available in [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).
