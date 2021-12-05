from time import perf_counter
from typing import Union

from pytube import YouTube, Playlist, Channel
from pytube.exceptions import RegexMatchError, VideoPrivate, VideoUnavailable


def main():
    program_loop()
    while download_more():
        program_loop()


def program_loop():
    url = get_url()
    if is_playlist(url):
        playlist(url)
    elif is_channel(url):
        channel(url)
    else:
        single_video(url)


def download_more() -> bool:
    choice = input('Do you want to download more? [y/n] ')
    return choice != 'n'


def get_url() -> str:
    url = input('Enter the URL of the YouTube video/playlist/channel you want to download: ')
    if not url:
        url = 'https://youtu.be/L1Buw5XPj_k'
    return url


def is_playlist(url: str) -> bool:
    return 'playlist' in url


def is_channel(url: str) -> bool:
    return 'channel' in url or 'user' in url


def channel(url: str):
    try:
        c = Channel(url)
        if not correct_channel_name(c):
            return
        download_channel(c)
    except RegexMatchError:
        print(f'{url} is not a valid channel url.')
    except KeyError:
        print(f'{url} is not available or is not a channel and cannot be downloaded.')


def correct_channel_name(c: Channel) -> bool:
    choice = input(f'Do you want to download all {len(c.videos)} (non-private) videos '
                   f'from the channel "{c.channel_name}"? [y/n] ')
    return choice != 'n'


def download_channel(c: Channel):
    download_playlist(c)


def playlist(url: str):
    try:
        p = Playlist(url)
        if not correct_playlist_title(p):
            return
        download_playlist(p)
    except RegexMatchError:
        print(f'{url} is not a valid playlist url.')
    except KeyError:
        print(f'{url} is not available or is not a playlist and cannot be downloaded.')


def correct_playlist_title(p: Playlist) -> bool:
    choice = input(f'Do you want to download all {len(p.videos)} (non-private) videos '
                   f'in the playlist with the title "{p.title}"? [y/n] ')
    return choice != 'n'


def download_playlist(p: Union[Playlist, Channel]):
    print()
    counter = 1
    for v in p.videos:
        print(f'Downloading video {counter} out of {len(p.videos)}.')
        print(f'Video title: "{v.title}"')
        v.register_on_progress_callback(progress_func)
        v.register_on_complete_callback(complete_func)
        download_video(v, p.title if type(p) is Playlist else p.channel_name)
        print()
        counter += 1


def single_video(url: str):
    try:
        yt = YouTube(url,
                     on_progress_callback=progress_func,
                     on_complete_callback=complete_func)
        if not correct_video_title(yt):
            return
        download_video(yt)
    except RegexMatchError:
        print(f'{url} is not a valid video url.')
    except VideoPrivate:
        print(f'{url} is a private video and cannot be downloaded.')
    except VideoUnavailable:
        print(f'{url} is unavailable to us and cannot be downloaded.')


def correct_video_title(yt: YouTube) -> bool:
    choice = input(f'Do you want to download the video with the title "{yt.title}"? [y/n] ')
    return choice != 'n'


def download_video(yt: YouTube, folder=''):
    video = yt.streams.get_highest_resolution()
    path = 'Downloads'
    if len(folder) > 0:
        path += '\\' + folder
    video.download(path)


def progress_func(stream, chunk, bytes_remaining):
    download_speed = calc_download_speed(bytes_remaining)
    print(
        f'\r{bytes_remaining // (1024 * 1024)} MB remaining \t' +
        f'Download speed: {download_speed} MB/s \t' +
        f'Est. time remaining: {calc_remaining_time(bytes_remaining, download_speed)} s\t\t',
        end='')


prev_bytes = 0
prev_time = 0


def calc_download_speed(bytes_remaining: int) -> float:
    global prev_bytes, prev_time
    if prev_bytes == 0:
        prev_bytes = bytes_remaining + 1
        prev_time = perf_counter()

    speed = round((prev_bytes - bytes_remaining) / (1024 * 1024) / (perf_counter() - prev_time), 1)

    prev_bytes = bytes_remaining
    prev_time = perf_counter()

    return speed


def calc_remaining_time(bytes_remaining: int, download_speed: float) -> int:
    return round(bytes_remaining / (1024 * 1024) / download_speed)


def complete_func(stream, file_path):
    print(f'\nDownload complete. Video saved to {file_path}')


if __name__ == '__main__':
    main()
