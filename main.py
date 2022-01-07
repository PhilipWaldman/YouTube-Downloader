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
best_res = False
default_res = False


def main():
    has_ffmpeg()
    program_loop_body()
    while download_more():
        program_loop_body()


def has_ffmpeg():
    """Checks whether FFmpeg is installed and sets the ffmpeg boolean flag."""
    try:
        run('ffmpeg -h', stderr=False, stdout=False, check=True, shell=True)
    except CalledProcessError:
        global ffmpeg
        ffmpeg = False


def program_loop_body():
    """The main program that gets repeated."""
    global resolution, best_res, default_res, use_progressive
    resolution = None
    best_res = False
    default_res = False
    use_progressive = False

    url = get_url()
    if is_playlist(url):
        playlist(url)
    elif is_channel(url):
        channel(url)
    else:
        single_video(url)


def download_more() -> bool:
    """Asks the user if they want to download anything else.

    :return: True if they want to download more; otherwise, False.
    """
    return yes_to_continue('Do you want to download more?')


def get_url() -> str:
    """Asks the user for the video/playlist/channel they want to download.

    :return: The URL of the content to download.
    """
    url = input('Enter the URL of the YouTube video/playlist/channel you want to download: ')
    # This is a debug feature, so I don't have to paste the video URL every time.
    if not url:
        url = 'https://youtu.be/L1Buw5XPj_k'
    return url


def is_playlist(url: str) -> bool:
    """Checks whether the URL is that of a playlist.

    :param url: The URL to check.
    :return: Whether the URL is a playlist.
    """
    return 'playlist' in url


def is_channel(url: str) -> bool:
    """Checks whether the URL is that of a channel/user.

    :param url: The URL to check.
    :return: Whether the URL is a channel/user.
    """
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
    """Asks the user if this is indeed the channel they want ot download.

    :param c: The channel is question.
    :return: Whether this is the correct channel.
    """
    return yes_to_continue(f'Do you want to download all {len(c.video_urls)} (non-private) videos from the '
                           f'channel "{c.channel_name}"?')


def download_channel(c: Channel):
    """Download all the video of this channel.

    :param c: The channel to download all videos from.
    """
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
    """Asks the user if this is indeed the playlist they want ot download.

    :param p: The playlist is question.
    :return: Whether this is the correct playlist.
    """
    return yes_to_continue(f'Do you want to download all {p.length} (non-private) videos in the playlist '
                           f'with the title "{p.title}"?')


def download_playlist(p: Union[Playlist, Channel]):
    """Download all the video of this playlist.

    :param p: The playlist to download all videos from.
    """
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
    """Asks the user if this is indeed the video they want ot download.

    :param yt: The video is question.
    :return: Whether this is the correct video.
    """
    return yes_to_continue(f'Do you want to download the video with the title "{yt.title}"?')


def download_video(yt: YouTube, folder=''):
    path = 'Downloads'
    if len(folder) > 0:
        path = join(path, folder)

    if not best_res and not default_res and (not resolution or not available_in_resolution(yt)):
        set_download_resolution(yt)
    elif best_res:
        set_best_resolution(yt)

    if not ffmpeg or use_progressive:
        download_progressive_video(yt, path)
    else:
        download_adaptive_video(yt, path)


def available_in_resolution(yt: YouTube) -> bool:
    """Checks if the video is available in the set resolution.

    :param yt: The video to check its resolution.
    :return: Whether it is available in the set resolution.
    """
    if use_progressive or not ffmpeg:
        selected_video_stream = yt.streams.filter(progressive=True, resolution=resolution).first()
    else:
        selected_video_stream = yt.streams.filter(adaptive=True, mime_type='video/webm', resolution=resolution).first()
    return selected_video_stream


def set_download_resolution(yt: YouTube):
    """Asks the user to select the resolution to download this video in.

    If this is a video in a playlist or channel, this will set the download resolution for all videos in the playlist.

    :param yt: The video to set the download resolution for.
    """
    global resolution, use_progressive, best_res, default_res

    progressive_streams = yt.streams.filter(progressive=True, type='video')
    p_res = {s.resolution for s in progressive_streams}
    p_res_max = max([int(i[:-1]) for i in p_res])
    if ffmpeg:
        adaptive_streams = yt.streams.filter(adaptive=True, type='video')
        a_res = {s.resolution for s in adaptive_streams if int(s.resolution[:-1]) > p_res_max}
    else:
        a_res = set()

    sorted_res = sort_resolutions(p_res | a_res, ascending=False)
    sorted_res.extend(["best", "default"])
    options_str = f'{sorted_res}'[1:-1] \
        .replace("'", '')
    prompt = f'At what resolution do you want to download the following video(s)?\n' \
             f'The options are: {options_str}\n' \
             f'Note: resolutions higher than {p_res_max}p use a different downloading method and take ' \
             f'*significantly* longer to download.\n' \
             f'Resolution: '
    choice = input(prompt).lower()
    all_choices = p_res | a_res
    all_choices |= {c[:-1] for c in all_choices}
    all_choices |= {'best', 'default'}
    while choice not in all_choices:
        choice = input(f'{choice} is not a valid resolution. The options are: {options_str} ').lower()

    if choice not in {'best', 'default'}:
        resolution = choice if choice.endswith('p') else f'{choice}p'
        int_res = int(resolution[:-1])
        use_progressive = int_res <= p_res_max
    elif choice == 'best':
        best_res = True
    else:
        default_res = True
        use_progressive = True


def set_best_resolution(yt: YouTube):
    """Sets the resolution to the highest resolution the video can be downloaded in.

    :param yt: The video in question.
    """
    global resolution, use_progressive

    progressive_streams = yt.streams.filter(progressive=True, type='video')

    p_res = {s.resolution for s in progressive_streams}
    if ffmpeg:
        adaptive_streams = yt.streams.filter(adaptive=True, type='video')
        a_res = {s.resolution for s in adaptive_streams}
    else:
        a_res = set()
    max_res = max([int(i[:-1]) for i in p_res | a_res])
    resolution = f'{max_res}p'
    use_progressive = max_res in p_res


def sort_resolutions(resolutions: Set[str], ascending=True) -> List[str]:
    """Sorts a set of resolution strings.

    :param resolutions: The unsorted set of resolution strings.
    :param ascending: Whether to sort in ascending or descending order.
    :return: The sorted list of resolution strings.
    """
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
    """Downloads the video as a progressive video to the given path.

    This method of downloading is faster than adaptive, but it is limited to a max resolution of 720p.

    :param yt: The video to download.
    :param path: The path to save the video to.
    """
    yt.register_on_progress_callback(progress_func)
    yt.register_on_complete_callback(complete_func)
    if default_res:
        video = yt.streams.get_highest_resolution()
    else:
        video = yt.streams.filter(resolution=resolution, progressive=True).first()
    video.download(path)


def download_adaptive_video(yt: YouTube, path: str):
    """Downloads the video as an adaptive video to the given path.

    This method of downloading is slower than progressive, but it can download higher resolutions.
    FFmpeg needs to be installed to this function to work. It downloads the video and audio separately and then
    combines them using FFmpeg.

    :param yt: The video to download.
    :param path: The path to save the video to.
    """
    # Download the separate video and audio files
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
    """Calculates the download speed of the last chunk that was downloaded.

    :param bytes_remaining: The number of bytes remaining to be downloaded.
    :return: The download speed in MB/s.
    """
    global prev_bytes, prev_time
    if prev_bytes == 0:
        prev_bytes = bytes_remaining + 1
        prev_time = perf_counter()

    speed = round((prev_bytes - bytes_remaining) / (1024 * 1024) / (perf_counter() - prev_time), 1)

    prev_bytes = bytes_remaining
    prev_time = perf_counter()

    return speed


def calc_remaining_time(bytes_remaining: int, download_speed: float) -> int:
    """Estimates how much time remaining for the download to complete.

    :param bytes_remaining: The number of bytes remaining to be downloaded.
    :param download_speed: The download speed in MB/s.
    :return: The estimated time remaining in s.
    """
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
