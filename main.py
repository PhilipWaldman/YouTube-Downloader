from os import remove
from os.path import join
from subprocess import run, CalledProcessError
from time import perf_counter
from typing import Union, Set, List

from pytube import YouTube, Playlist, Channel
from pytube.exceptions import RegexMatchError, VideoPrivate, VideoUnavailable

ffmpeg = True
use_progressive = False
resolution = None


def main():
    has_ffmpeg()
    program_loop_body()
    while download_more():
        program_loop_body()


def has_ffmpeg():
    try:
        run('ffmpeg -h', stderr=False, stdout=False, check=True, shell=True)
    except CalledProcessError:
        global ffmpeg
        ffmpeg = False


def program_loop_body():
    global resolution
    resolution = None
    url = get_url()
    if is_playlist(url):
        playlist(url)
    elif is_channel(url):
        channel(url)
    else:
        single_video(url)


def download_more() -> bool:
    return yes_to_continue('Do you want to download more?')


def get_url() -> str:
    url = input('Enter the URL of the YouTube video/playlist/channel you want to download: ')
    # This is a debug feature, so I don't have to paste the video URL every time.
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
    return yes_to_continue(f'Do you want to download all {len(c.video_urls)} (non-private) videos from the '
                           f'channel "{c.channel_name}"?')


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
    return yes_to_continue(f'Do you want to download all {p.length} (non-private) videos in the playlist '
                           f'with the title "{p.title}"?')


def download_playlist(p: Union[Playlist, Channel]):
    print()
    if type(p) is Playlist:
        n_videos = p.length
    else:
        n_videos = len(p.video_urls)
    counter = 1
    for v in p.videos:
        print(f'Downloading video {counter} out of {n_videos}.')
        print(f'Video title: "{v.title}"')
        download_video(v, p.title if type(p) is Playlist else p.channel_name)
        print()
        counter += 1


def single_video(url: str):
    try:
        yt = YouTube(url)
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
    return yes_to_continue(f'Do you want to download the video with the title "{yt.title}"?')


def download_video(yt: YouTube, folder=''):
    path = 'Downloads'
    if len(folder) > 0:
        path = join(path, folder)

    if not resolution:
        set_download_resolution(yt)

    if not ffmpeg or use_progressive:
        download_progressive_video(yt, path)
    else:
        download_adaptive_video(yt, path)


def set_download_resolution(yt: YouTube):
    progressive_streams = yt.streams.filter(progressive=True, type='video')
    adaptive_streams = yt.streams.filter(adaptive=True, type='video')

    p_res = {s.resolution for s in progressive_streams}
    p_res_max = max([int(i[:-1]) for i in p_res])
    a_res = {s.resolution for s in adaptive_streams if int(s.resolution[:-1]) > p_res_max}

    options_str = f'{sort_resolutions(p_res | a_res, ascending=False)}'[1:-1].replace("'", '')
    prompt = f'At what resolution do you want to download the following video(s)?\n' \
             f'The options are: {options_str}\n' \
             f'Note: resolutions higher than {p_res_max}p use a different downloading method and take ' \
             f'significantly longer to download.\n' \
             f'Resolution: '
    choice = input(prompt)
    all_choices = p_res | a_res
    all_choices |= {c[:-1] for c in all_choices}
    while choice not in all_choices:
        choice = input(f'{choice} is not a valid resolution. The options are: {options_str} ')
    global resolution
    resolution = choice if choice.endswith('p') else f'{choice}p'

    int_res = int(resolution[:-1])
    global use_progressive
    use_progressive = int_res <= p_res_max


def sort_resolutions(resolutions: Set[str], ascending=True) -> List[str]:
    res_dict = {int(r[:-1]): r for r in resolutions}
    sorted_res = []
    while len(res_dict) > 0:
        if ascending:
            cur_res = min(res_dict.keys())
        else:
            cur_res = max(res_dict.keys())
        sorted_res.append(res_dict[cur_res])
        res_dict.pop(cur_res)
    return sorted_res


def download_progressive_video(yt: YouTube, path: str):
    yt.register_on_progress_callback(progress_func)
    yt.register_on_complete_callback(complete_func)
    video = yt.streams.filter(resolution=resolution, progressive=True).first()
    video.download(path)


def download_adaptive_video(yt: YouTube, path: str):
    # Download the separate video and audio files
    # .first() downloads the lowest resolution video file. This is to reduce testing time.
    print('Downloading video and audio files...')
    video = yt.streams.filter(adaptive=True, mime_type='video/webm', resolution=resolution).first()
    audio = yt.streams.get_audio_only(subtype='webm')
    if not video or not audio:
        download_progressive_video(yt, path)
        return
    yt.register_on_progress_callback(progress_func)
    video_path = video.download(path, filename_prefix='video_')
    audio_path = audio.download(path, filename_prefix='audio_')
    print()

    # Combine the video and audio files
    print('Combining video and audio files...')
    cmd = ['ffmpeg', '-y', '-i', audio_path, '-i', video_path,
           join(path, video.default_filename.replace('webm', 'mp4'))]
    try:
        run(cmd, stderr=False, stdout=False, check=True, shell=True)
    except CalledProcessError:
        download_progressive_video(yt, path)

    # Remove the separate video and audio files
    print('Removing the separate video and audio files...')
    try:
        remove(video_path)
    except FileNotFoundError:
        pass
    try:
        remove(audio_path)
    except FileNotFoundError:
        pass


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


def yes_to_continue(prompt: str) -> bool:
    """ Asks the user the prompt. The prompt gets asked again as long as the user doesn't answer either 'y' or 'n'.
    Returns True when the user answers 'y' and returns False when the user answer 'n'.

    :param prompt: The prompt to ask the user.
    :return: True when the user enters 'y', False when the user enters 'n'.
    """
    choices = {'n', 'y'}
    choice = input(f'{prompt} [y/n] ').lower()
    while choice not in choices:
        choice = input(f'Please only answer with [y/n]: {prompt} ').lower()
    return choice == 'y'


if __name__ == '__main__':
    main()
