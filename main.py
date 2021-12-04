from time import perf_counter

from pytube import YouTube, Playlist


def main():
    program_loop()
    while download_more():
        program_loop()


def program_loop():
    url = get_url()
    if is_playlist(url):
        playlist(url)
    else:
        single_video(url)


def download_more():
    choice = input('Do You want to download more? [y/n] ')
    return False if choice == 'n' else True


def get_url():
    url = input('Enter the URL of the YouTube video/playlist you want to download: ')
    if not url:
        url = 'https://youtu.be/L1Buw5XPj_k'
    return url


def is_playlist(url):
    return 'playlist' in url


def playlist(url):
    p = Playlist(url)
    if not correct_playlist_title(p):
        return
    download_playlist(p)


def correct_playlist_title(p):
    choice = input(f'Do you want to download all {p.length} videos in the playlist with the title "{p.title}"? [y/n] ')
    if choice == 'n':
        return False
    return True


def download_playlist(p):
    counter = 1
    for v in p.videos:
        print()
        print(f'Downloading video {counter} out of {p.length}.')
        print(f'Video title: "{v.title}"')
        v.register_on_progress_callback(progress_func)
        download_video(v)
        print()
        counter += 1


def single_video(url):
    yt = YouTube(url,
                 on_progress_callback=progress_func,
                 on_complete_callback=complete_func)
    if not correct_video_title(yt):
        return
    download_video(yt)


def correct_video_title(yt):
    choice = input(f'Do you want to download the video with the title "{yt.title}"? [y/n] ')
    if choice == 'n':
        return False
    return True


def download_video(yt):
    video = yt.streams.get_highest_resolution()
    video.download('Downloads')


def progress_func(stream, chunk, bytes_remaining):
    download_speed = calc_download_speed(bytes_remaining)
    print(
        f'\r{bytes_remaining // (1024 * 1024)} MB remaining \t' +
        f'Download speed: {download_speed} MB/s \t' +
        f'Est. time remaining: {calc_remaining_time(bytes_remaining, download_speed)} s\t\t',
        end='')


prev_bytes = 0
prev_time = 0


def calc_download_speed(bytes_remaining):
    global prev_bytes, prev_time
    if prev_bytes == 0:
        prev_bytes = bytes_remaining + 1
        prev_time = perf_counter()

    speed = round((prev_bytes - bytes_remaining) / (1024 * 1024) / (perf_counter() - prev_time), 1)

    prev_bytes = bytes_remaining
    prev_time = perf_counter()

    return speed


def calc_remaining_time(bytes_remaining, download_speed):
    return round(bytes_remaining / (1024 * 1024) / download_speed)


def complete_func(stream, file_path):
    print(f'\nDownload complete. Video saved to {file_path}')


if __name__ == '__main__':
    main()
