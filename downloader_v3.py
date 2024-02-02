import sys
import os
import requests
import glob
from pytube import YouTube, Playlist
from multiprocessing import Pool, Manager, freeze_support
from itertools import repeat
from time import sleep

# =======================================================================================================================

class Options:
    def __init__(self, workspace):
        self.workspace = workspace
        self.options = self.option_select()

    # -----------------------------------------------------------------------------------------------------------------------

    def option_select(self):
        def documentation():
            print('\n' + 'Documentation'.center(60, '-'))
            print('urltxt - generates a url text file for bulk url input')
            print('ts - generates a timestamp text file by which you input urls and timestamps accordingly')
            print()
            print('dts - if any of the given videos have timestamps in their descriptions, video will be stripped into its respective timestamps')
            print()
            print('dp - specify a custom video download path')
            print('fdry - will search for the default Foundry installation path and download files to its location if found')
            print()
            print('fproc - increase processing time at the risk of increased processor strain. If the app crashes, this is why :)')
            print()
            print('Ensure you separate multiple option inputs with commas')
            print('Press enter if you do not wish to select any options')
            print()
            print('If you have any additional questions or recommendations for improving the script, message Dan')

        # --------------------------------------------

        selection = ['urltxt', 'ts', 'dts', 'dp', 'fdry', 'fproc']
        option_dict = {}
        for item in selection:
            if item == 'fproc':
                option_dict[item] = (1, 2 / 3)
            else:
                option_dict[item] = 0

        while True:
            options = input(
                '\nInput additional options (comma separated; type help for documentation; press enter to skip): \n>>').strip().split(',')

            if 'help' in options:
                documentation()
            else:
                break

        for option in options:
            option = option.strip()

            if option == 'urltxt':
                if option_dict['ts'] == 0:
                    option_dict['urltxt'] = 1
                    self.urltxt()
            elif option == 'ts':
                if option_dict['urltxt'] == 0:
                    option_dict['ts'] = 1
                    self.ts()

            elif option == 'dts':
                option_dict['dts'] = 1

            elif option == 'dp':
                if option_dict['fdry'] == 0:
                    option_dict['dp'] = 1
                    self.dp()
            elif option == 'fdry':
                if option_dict['dp'] == 0:
                    option_dict['fdry'] = 1
                    self.fdry()

            elif option == 'fproc':
                option_dict['fproc'] = (2, 1)
            elif option == '':
                pass
            else:
                print(f'WARNING {option} is not a valid option')

        return option_dict

    # -----------------------------------------------------------------------------------------------------------------------

    def urltxt(self):
        def create_file():
            print('\nCreating url_inputs.txt...')
            with open(txtpath, 'w') as w:
                w.write('Paste video/playlist URLs in this text file, each on a new line\n')

            input('\nInput URLs in the url_inputs.txt file and then press enter\n>> ')

        txtpath = os.path.join(self.workspace['fpath'], 'url_inputs.txt')
        self.workspace['urltxt'] = txtpath

        if not os.path.exists(txtpath):
            create_file()
        else:
            print('\nurl_inputs.txt Found.')

            while True:
                consent = input('Would you like to use existing file? [y]/n:\n>> ').lower().strip()
                if consent == '' or consent == 'y':
                    break
                elif consent == 'n':
                    create_file()
                    break
                else:
                    print('Invalid input\n')

    # -----------------------------------------------------------------------------------------------------------------------

    def ts(self):
        def create_file():
            print('\nCreating timestamp_inputs.txt...')
            with open(tspath, 'w') as w:
                w.write(
                    'https://www.youtube.com/watch?v=dQw4w9WgXcQ\n00:00 Name of Timestamp 1\n04:20 Name of Timestamp 2\n\nhttps://www.youtube.com/watch?v=FveF-we6lcE\n00:00 Name of Timestamp 1\netc.\n')

            input('\nInput URLs and timestamps in the timestamp_inputs.txt file and then press enter\n>> ')

        tspath = os.path.join(self.workspace['fpath'], 'timestamp_inputs.txt')
        self.workspace['ts'] = tspath

        if not os.path.exists(tspath):
            create_file()
        else:
            print('\ntimestamp_inputs.txt Found.')

            while True:
                consent = input('Would you like to use existing file? [y]/n:\n>> ').lower().strip()
                if consent == '' or consent == 'y':
                    break
                elif consent == 'n':
                    create_file()
                    break
                else:
                    print('Invalid input\n')

    # -----------------------------------------------------------------------------------------------------------------------

    def dp(self):
        path = input('Input desired download path:\n>> ').strip().replace('"', '').replace("'", "")

        self.workspace['dp'] = path

    # -----------------------------------------------------------------------------------------------------------------------

    def fdry(self):
        foundry = os.path.join(os.getenv('LOCALAPPDATA'), 'FoundryVTT')

        if os.path.exists(foundry):
            foundry = os.path.join(foundry, 'Data', 'music', 'download')
            print(f'\nFoundryVTT found. Creating download folder in the following path:\n{foundry}')

            if not os.path.exists(foundry):
                os.makedirs(foundry)
                self.workspace['fdry'] = foundry
        else:
            print(f'WARNING FoundryVTT not found in the default location:\n{foundry}')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Downloader:
    def __init__(self):
        self.workspace = {}
        self.runflag = 1

        if self.check_install() == 0:
            self.runflag = 0
            self.options = Options(self.workspace).options
            self.urls, self.filetype, self.bitrate, self.timestamps = self.user_input(self.options)

    # -----------------------------------------------------------------------------------------------------------------------

    def check_install(self):
        DLINK = r'https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z'
        extraction_flag = 0

        if getattr(sys, 'frozen', False):
            current_dir = os.path.dirname(sys.executable)
        else:
            current_dir = os.path.dirname(__file__)
        ffmpeg_drive_dir = os.path.join(current_dir, 'ffmpeg')

        if not os.path.exists(ffmpeg_drive_dir):
            print('\nffmpeg is required for this script to function.')
            consent = input(f'Allow its installation in the file directory? ([y]/n)\n>> ').lower()

            if 'y' in consent or consent == '' or consent == ' ':
                pass
            else:
                return True

            os.system(f"mkdir {ffmpeg_drive_dir}")

            print('\nObtaining ffmpeg...')
            ffmpeg_zip = 'ffmpeg.7z'
            with requests.get(DLINK, stream=True) as r:
                r.raise_for_status()
                with open(ffmpeg_zip, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            input('Done. Press enter once you\'ve extracted the contents of the zip file to the "ffmpeg" folder\n>> ')

            files = glob.glob(os.path.join(current_dir, 'ffmpeg', '*'))
            if len(files) == 0:
                extraction_flag = 1
            else:
                try:
                    os.remove(ffmpeg_zip)
                except FileNotFoundError:
                    pass

        files = glob.glob(os.path.join(current_dir, 'ffmpeg', '*'))
        if len(files) == 1:
            file = files[0]
            ffmpeg_path = os.path.join(current_dir, 'ffmpeg', file, 'bin')
        elif len(files) == 0:
            extraction_flag = 1
        else:
            ffmpeg_path = os.path.join(current_dir, 'ffmpeg', 'bin')

        os.environ["PATH"] += os.pathsep + ffmpeg_path

        self.workspace['fpath'] = current_dir

        return extraction_flag

    # -----------------------------------------------------------------------------------------------------------------------

    def user_input(self, options):
        def url_input():
            processed_urls = []
            playlist = []
            stamps_container = []
            titles_container = []

            if options['urltxt'] == 1:
                with open(self.workspace['urltxt'], 'r') as r:
                    urls = r.read().replace('Paste video/playlist URLs in this text file, each on a new line',
                                            '').strip().splitlines()
            elif options['ts'] == 1:
                with open('timestamp_inputs.txt', 'r') as r:
                    content = r.read().replace(
                        'https://www.youtube.com/watch?v=dQw4w9WgXcQ\n00:00 Name of Timestamp 1\n04:20 Name of Timestamp 2\n\nhttps://www.youtube.com/watch?v=FveF-we6lcE\n00:00 Name of Timestamp 1\netc.',
                        '').strip()

                urls = []
                for line in content.splitlines():
                    if 'youtube.com' in line:
                        urls.append(line.strip())
                        content = content.replace(urls[-1] + '\n', '')

                stamps_container = []
                titles_container = []
                temp_stamps = []
                temp_titles = []
                for line in content.splitlines():
                    line = line.split()
                    if len(line) == 0:
                        stamps_container.append(temp_stamps)
                        titles_container.append(temp_titles)
                        temp_stamps = []
                        temp_titles = []
                    else:
                        for idx, item in enumerate(line):
                            if ':' in item:
                                break

                        line = line[idx:]

                        stamp = line.pop(0)
                        stamp = stamp.split(':')
                        try:
                            if len(stamp) == 2:
                                stamp = int(stamp[0]) * 60 + int(stamp[1])
                            else:
                                stamp = int(stamp[0]) * 3600 + int(stamp[1]) * 60 + int(stamp[2])
                        except ValueError:
                            continue

                        temp_stamps.append(stamp)
                        temp_titles.append(' '.join(line))
                stamps_container.append(temp_stamps)
                titles_container.append(temp_titles)
            else:
                urls = input('\nEnter video/playlist URL (comma separated for multiple)\n>> ').split(',')

            for url in urls:
                if 'playlist' in url:
                    playlist += list(Playlist(url).video_urls)
                else:
                    url = url.split('&')[0].strip()
                    if 'youtu.be' in url:
                        url = 'https://www.youtube.com/watch?v=' + url.split('/')[-1]
                    elif 'https' not in url:
                        url = 'https://' + url
                    processed_urls.append(url)

            processed_urls += playlist

            stamp_flag = 0
            for stamp in stamps_container:
                if stamp != '':
                    stamp_flag = 1
                    break

            if stamp_flag == 0:
                return processed_urls, ['']*len(processed_urls)
            else:
                timestamp_container = []
                for idx, item in enumerate(titles_container):
                    timestamp_container.append(dict(zip(titles_container[idx], stamps_container[idx])))

                return processed_urls, timestamp_container

        # ---------------------------------------------------------------------------------------------------------------

        def filetype_input():
            while True:
                filetype = input('\nSelect file format\n>> ').lower().replace('.', '')
                if filetype in ['mp4', 'webm']:
                    filetype = (f'{filetype}', 'video')
                    break
                elif filetype in ['mp3', 'ogg', 'wav']:
                    filetype = (f'{filetype}', 'audio')
                    break
                else:
                    print(f'\nFiletype .{filetype} not supported')

            return filetype

        # ---------------------------------------------------------------------------------------------------------------

        def bitrate_input():
            while True:
                bitrate = input('\nInput desired bitrate in kbps (Press enter for max)\n>> ').lower().strip()

                if bitrate == '' or bitrate == ' ':
                    return ''

                try:
                    bitrate = float(bitrate)
                    bitrate = f'{bitrate}k'
                    break
                except ValueError:
                    print('Invalid input')

            return bitrate

        # ---------------------------------------------------------------------------------------------------------------

        url_container, timestamps = url_input()

        return url_container, filetype_input(), bitrate_input(), timestamps

    # -----------------------------------------------------------------------------------------------------------------------

    def initialize_download_path(self):
        if self.options['dp'] == 1:
            self.workspace['dpath'] = self.workspace['dp']

        elif self.options['fdry'] == 1:
            self.workspace['dpath'] = self.workspace['fdry']

        else:
            if getattr(sys, 'frozen', False):
                download_path = os.path.dirname(sys.executable)
            elif __file__:
                download_path = os.path.dirname(__file__)
            download_path = os.path.join(download_path, 'download')

            if not os.path.exists(download_path):
                os.system("mkdir download")
                print('\nCreated download directory')
            else:
                print('\nDownload directory found')

            self.workspace['dpath'] = download_path

        os.chdir(self.workspace['dpath'])

    # -----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def fetch_streams(feed, shared_list, filetype, options, ts, timestamp_list):
        file = YouTube(feed, use_oauth=True, allow_oauth_cache=True)
        filetype = filetype[1]
        timestamp_dict = ''

        if options['dts'] == 1:
            description = file.description
            timestamp_dict = {}

            if ':' in description:
                for line in description.splitlines():
                    if ':' in line:
                        try:
                            int(line[line.find(':') - 1])
                            line = line.strip().split()

                            for idx, item in enumerate(line):
                                if ':' in item:
                                    break

                            line = line[idx:]

                            stamp = line.pop(0)
                            stamp = stamp.split(':')
                            if len(stamp) == 2:
                                stamp = int(stamp[0]) * 60 + int(stamp[1])
                            else:
                                stamp = int(stamp[0]) * 3600 + int(stamp[1]) * 60 + int(stamp[2])

                            title = ' '.join(line)

                            timestamp_dict[title] = stamp
                        except ValueError:
                            continue

                titles = list(timestamp_dict.keys())
                stamps = list(timestamp_dict.values())
                length = file.length

                for idx, stamp in enumerate(stamps):
                    if stamp == stamps[-1]:
                        stamps[idx] = (stamp, length + 1)
                    else:
                        stamps[idx] = (stamp, stamps[idx + 1] + 1)

                timestamp_dict = dict(zip(titles, stamps))

            if len(timestamp_dict) == 0:
                timestamp_dict = ''

        elif options['ts'] == 1:
            stamps = list(ts.values())
            titles = list(ts.keys())
            length = file.length

            for idx, stamp in enumerate(stamps):
                if stamp == stamps[-1]:
                    stamps[idx] = (stamp, length + 1)
                else:
                    stamps[idx] = (stamp, stamps[idx + 1] + 1)

            timestamp_dict = dict(zip(titles, stamps))

        if filetype == 'audio':
            file = file.streams.get_audio_only()
        else:
            file = file.streams.get_highest_resolution()

        file_name = file.default_filename

        package = (file, file_name)

        print(f'Found {file_name}')

        shared_list.append(package)
        timestamp_list.append(timestamp_dict)

    # -----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def download(package):
        file, file_name = package
        files_present = glob.glob(f'{file_name}')

        if len(files_present) == 0:
            file.download()
            print(f'\nDownloaded {file_name}')
        else:
            print(f'\n{file_name} already downloaded')

    # -----------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def convert(package, filetype, bitrate, timestamp, dpath):
        def ffmpeg(file_name, ext, filetype, timestamp, bitrate, dpath):
            os.chdir(dpath)

            if type(timestamp) == str:
                if bitrate == '':
                    os.system(f'ffmpeg -y -i "{file_name}" "{file_name.replace(ext, f".{filetype}")}"')
                else:
                    os.system(
                        f'ffmpeg -y -i "{file_name}" -b:v {bitrate} -b:a {bitrate} "{file_name.replace(ext, f".{filetype}")}"')
            elif type(timestamp) == dict:
                dpath = os.path.join(dpath, file_name.replace(ext, ''))
                if not os.path.exists(dpath):
                    os.makedirs(dpath)

                for title, stamps in timestamp.items():
                    title = title.replace('.', '').replace(':', '').replace(';', '').replace(',', '').replace('"', '')\
                        .replace("'", "")

                    if bitrate == '':
                        os.system(f'ffmpeg -y -i "{file_name}" -ss {stamps[0]} -to {stamps[1]} "{os.path.join(dpath, title + f".{filetype}")}"')
                    else:
                        os.system(f'ffmpeg -y -i "{file_name}" -b:v {bitrate} -b:a {bitrate} -ss {stamps[0]} -to {stamps[1]} "{os.path.join(dpath, title + f".{filetype}")}"')

            os.remove(file_name)

            #-----------------------------------------------------------------------------------------------------------

        _, file_name = package
        filetype = filetype[0]

        ext = file_name[file_name.find('.'):]

        ffmpeg(file_name, ext, filetype, timestamp, bitrate, dpath)

        print(f'\n{file_name} Converted')


# =======================================================================================================================

if __name__ == '__main__':
    freeze_support()

    downloader = Downloader()

    if downloader.runflag == 0:
        stream_list = Manager().list()

        timestamps = Manager().list()

        procspeed = downloader.options['fproc']

        print('\nFetching YouTube streams...\n')
        with Pool(os.cpu_count() * procspeed[0]) as p:
            p.starmap(downloader.fetch_streams, zip(downloader.urls, repeat(stream_list),
                                                    repeat(downloader.filetype), repeat(downloader.options),
                                                    downloader.timestamps, repeat(timestamps)))

        downloader.initialize_download_path()

        print('\nDownloading YouTube streams...\n')
        with Pool((os.cpu_count() * procspeed[0])) as p:
            p.map(downloader.download, stream_list)

        print('\nBeginning conversions...\n')
        with Pool(int(os.cpu_count() * procspeed[-1])) as p:
            p.starmap(downloader.convert, zip(stream_list, repeat(downloader.filetype), repeat(downloader.bitrate),
                                              timestamps, repeat(downloader.workspace['dpath'])))

        input('\nFinished... Press enter to complete the contract\n>> ')
        print('You now owe me a facet of your soul :)')
        sleep(.25)

# todo default filetype to mp3
# todo fix ts option
