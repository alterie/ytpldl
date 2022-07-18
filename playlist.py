from mutagen.id3 import ID3, APIC
import requests
import validators
from pytube import YouTube
from tqdm import tqdm
from moviepy.editor import *
from PIL import Image
import shutil

base_url = "https://youtube.googleapis.com/youtube/v3/"
plid = "PLd3pZW4RUs2a8c30IwsUIREWYanKCZv2u"
api_key = "AIzaSyAMoR0rgiHtdbWDpbg2dbef1_X1_Qa46Pg"

output_dir = 'output'
tmp_dir = 'tmp'

err = []
wrn = []
inf = []

meds = []

def construct_url(api_key, parts, playlist, results):
    auth_url = base_url + f"playlistItems?key={api_key}"
    for part in parts:
        auth_url += f"&part={part}"

    if validators.url(playlist):
        playlist = playlist.split("=")[1]
    auth_url = auth_url + f'&maxResults={results}'
    constructed = auth_url + "&playlistId=" + playlist
    return constructed

def delete_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))

def construct_data(url):
    data = []
    req = requests.get(url)
    playlistItems = req.json()['items']

    for playlistItem in tqdm(playlistItems, "Indexing songs"):
        snippet = playlistItem['snippet']
        try:
            data.append(
                {
                    'name': snippet['title'],
                    'v_id': snippet['resourceId']['videoId'],
                    'cover': {
                        'url': snippet['thumbnails']['maxres']['url'],
                        'width': snippet['thumbnails']['maxres']['width'],
                        'height': snippet['thumbnails']['maxres']['height']
                    }
                }
            )
        except Exception:
            print(f"\n[YTPDL/ERR] `maxres` option not supported for song: {snippet['title']}. Switching to `medium` resolution. This will substantially lower the quality.")
            data.append(
                {
                    'name': snippet['title'],
                    'v_id': snippet['resourceId']['videoId'],
                    'cover': {
                        'url': snippet['thumbnails']['medium']['url'],
                        'width': snippet['thumbnails']['medium']['width'],
                        'height': snippet['thumbnails']['medium']['height']
                    }
                }
            )
            wrn.append(f"Unable to find `maxres` option for {snippet['title']}")
            meds.append(snippet['title'])

    return data

def download_video(data, outputdir):
    for video in tqdm(data, 'Downloading songs'):
        url = "https://www.youtube.com/watch?v=" + video['v_id']
        try:
            YouTube(url).streams.filter(progressive=True, file_extension='mp4').first().download(outputdir)
        except Exception:
            print(f"\n[YTPDL/WARN] `{video['name']}` is not available! Skipping.")
            err.append(f"Skipped {video['name']}; not available.")

def process_video(outputdir):
    for video in os.listdir(outputdir):
        if video.endswith(".mp4"):
            videoclip = VideoFileClip(outputdir+'/'+video)
            audioclip = videoclip.audio
            audioclip.write_audiofile(outputdir+'/'+video.replace(".mp4", ".mp3"))
            audioclip.close()
            videoclip.close()

    for video in os.listdir(outputdir):
        if video.endswith(".mp4"):
            os.remove(os.path.join(outputdir, video))

def add_cover_art(mp3file, albumart):
    audio = ID3(mp3file.replace(".", "").replace("mp3", "").replace("'", "").replace("$", "") + '.mp3')

    with open(albumart, 'rb') as albumart:
        audio['APIC'] = APIC(
            encoding=3,
            mime='image/jpeg',
            type=3, desc=u'Cover',
            data=albumart.read()
        )

    audio.save()

def download_image(link, name):
    img_data = requests.get(link).content
    with open(f'{name}.jpg', 'wb') as handler:
        handler.write(img_data)

def process_image(image, title):
    im = Image.open(image+'.jpg')

    im1 = im.crop((280, 0, 1000, 720))
    if title in meds:
        im1 = im.crop((70, 0, 250, 180))

    im1.save(f'{image}.jpg')


def convert_metadata(outputdir, tmpdir, data):
    for song in data:
        try:
            title = song['name']
            albumart = song['cover']['url']
            mp3file = f'{outputdir}/{title}.mp3'
            download_image(albumart, f'{tmpdir}/{title}')
            process_image(f'{tmpdir}/{title}', title)
            add_cover_art(mp3file, f'{tmpdir}/{title}.jpg')
        except Exception:
            wrn.append(f"{song['name']} not found in directory.")
            print(f"\n[YTPDL/ERR] `{song['name']}` was not found! Though, you were probably warned about this earlier.")

def finish_cleanup(output, tmpdir, outzip):
    print("Cleaning up preparing songs...")
    shutil.make_archive(outzip, 'zip', 'output')
    delete_folder(output)
    delete_folder(tmpdir)
    os.rmdir(output)
    os.rmdir(tmpdir)

def setup(output_dir, tmp_dir):
    try:
        os.mkdir(output_dir)
    except FileExistsError:
        pass
    try:
        os.mkdir(tmp_dir)
    except FileExistsError:
        pass

def print_summary():


    if len(inf) == 0:
        inf.append("None")
    if len(wrn) == 0:
        wrn.append("None")
    if len(err) == 0:
        err.append("None")
    print("------- YTPDL SUMMARY -------")
    print(f"info: {len(inf)} | warn: {len(wrn)} | err: {len(err)} ")
    print("----------- Info -----------")
    for info in inf:
        print("- " + info)
    print("--------- Warnings ---------")
    for warns in wrn:
        print("- " + warns)
    print("---------- Errors ----------")
    for errs in err:
        print("- " + errs)
    print("----- YTPDL SUMMARY END -----")


def generate(output_dir, tmp_dir, playlist, outzip):
    setup(output_dir, tmp_dir)
    url = construct_url(api_key, ['snippet', 'id'], playlist, 200)
    print(url)
    data = construct_data(url)
    download_video(data, output_dir)
    process_video(output_dir)
    convert_metadata(output_dir, tmp_dir, data)
    finish_cleanup(output_dir, tmp_dir, outzip)
    print_summary()
    print("YTPDL by ddozzi!")

def main():
    generate(output_dir, tmp_dir, 'https://music.youtube.com/playlist?list=PL7dhRqQS39Gpe3_7toj5oglAvdqXJxYTr&feature=share')

if __name__ == '__main__':
    main()
