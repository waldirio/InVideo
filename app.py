"""
docstring here
"""
import multiprocessing
import os
import tempfile
import shutil
import time
import imagesize
# import uuid
from flask import Flask, request, render_template, redirect, send_file
from exif import Image
from moviepy import vfx, ImageClip, concatenate_videoclips, VideoFileClip
from werkzeug.utils import secure_filename


app = Flask(__name__)


# # Generate a random UUID for user session
# my_uuid = uuid.uuid4()
# # Convert the UUID object to a string
# uuid_str = str(my_uuid)
# # Extract the first 8 characters
# USER_ID = uuid_str[:8]

# print(f"UUID object: {my_uuid}")
# print(f"UserID: {USER_ID}")

# Specify a directory to store uploaded files.
UPLOAD_FOLDER = 'images/'
# IMAGES_DIR = 'images/'
# UPLOAD_FOLDER = f"{USER_ID}/{IMAGES_DIR}"
# File extensions the system will accept.
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
print(f"PATH fotos: {UPLOAD_FOLDER}")

HEIGHT_DEFAULT = 1080
clips = []
FILES_PATH = os.path.join(app.config['UPLOAD_FOLDER'])
PATH_VIDEO_TEMP = "static/out_temp.mp4"
PATH_VIDEO = "static/output.mp4"
TIME = 3
FADEIN_TIME = 0.2
FADEOUT_TIME = 0.2

# Create the uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    """
    It will ensure that only the defined extensions are accepted when uploading files.
    """ 
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Make crop on images greater then 1920 x 1080
def crop_image(img_height, img_width, file):
    """
    It will define default height and width according to the image's position
     (vertical or horizontal).
    """
    # Vertical image
    if img_height > img_width:
        width_default = 1080
        clip = ImageClip(app.config['UPLOAD_FOLDER'] + file)
        clip = clip.with_effects([vfx.Resize(height=HEIGHT_DEFAULT)])
        new_width, new_height = clip.size
        new_height_center = new_height / 2
        y1_pos = new_height_center - (HEIGHT_DEFAULT / 2)
        y2_pos = new_height_center + (HEIGHT_DEFAULT / 2)
        clip = clip.with_effects([
            vfx.Crop(x1=0, y1=y1_pos, x2=width_default, y2=y2_pos)])
    else:
        # Horizonte image
        width_default = 1920
        clip = ImageClip(app.config['UPLOAD_FOLDER'] + file)
        clip = clip.with_effects([vfx.Resize(width=width_default)])
        new_width, new_height = clip.size
        new_height_center = new_height / 2
        y1_pos = new_height_center - (HEIGHT_DEFAULT / 2)
        y2_pos = new_height_center + (HEIGHT_DEFAULT / 2)
        clip = clip.with_effects([
            vfx.Crop(x1=0, y1=y1_pos, x2=width_default, y2=y2_pos)])

    return clip


def upload_files():
    """
    It will be responsible for uploading only files with the defined extensions.
    """
    if request.method == 'POST':
        # Get the list of files
        if 'files' not in request.files:
            return 'No files part'
        files = request.files.getlist('files')
        if files == []:
            return 'No files selected'
        elif files:
            temp_dir = tempfile.mkdtemp()
            # Save each file to the uploads directory
            for file in files:
                if file and allowed_file(file.filename):
                    # secure_filename resolving file with space in name               
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(temp_dir, filename.lower()))
            for file in files:
                # secure_filename resolving file with space in name
                filename = secure_filename(file.filename)
                shutil.copy(os.path.join(temp_dir, filename), UPLOAD_FOLDER)
            shutil.rmtree(temp_dir)
            return 'Files uploaded successfully.'
        else:
            return 'No files uploaded.'
    return None


def process_video():
    """
    It will be responsible for concatenating the existing files
     in the user's directory and processing the video at the end.
    """
    ratio_hd = round(1920 / 1080, 2)

    # Using sorted to sort the list of files
    # https://docs.python.org/3/howto/sorting.html
    for file in sorted(os.listdir(app.config['UPLOAD_FOLDER'])):
        if file.endswith(".jpg") or file.endswith(".jpeg") or file.endswith(".png"):
            with open("images/" + file, "rb") as image_file:
                file_exif = Image(image_file)
                try:
                    img_height = file_exif.image_height
                    img_width = file_exif.image_width
                except AttributeError:
                    img_width, img_height = imagesize.get(app.config['UPLOAD_FOLDER'] + file)
                except KeyError:
                    img_width, img_height = imagesize.get(app.config['UPLOAD_FOLDER'] + file)

                # Check the aspect ratio, and if diff of 1.77, crop the image
                ratio = round(img_height / img_width, 2)
                if ratio != ratio_hd:
                    clip = crop_image(img_height, img_width, file)
                else:
                    # if ratio == ratio_hd, it's necessary to create the first clip entry
                    # clip = ImageClip(app.config['UPLOAD_FOLDER'] + file)
                    clip = crop_image(img_height, img_width, file)
                    

                print(f"DEBUG: {file_exif.has_exif} {img_height} {img_width} {clip}")

                if file_exif.has_exif:
                    try:

                        if file_exif.orientation in (1, 2):
                            clips.append(clip.with_duration(TIME).with_effects([vfx.FadeIn(FADEIN_TIME), vfx.FadeOut(FADEOUT_TIME)]))
                        elif file_exif.orientation in (6, 7):
                            clip = clip.with_duration(TIME)
                            clip = clip.with_effects([vfx.Resize(width=1080)])
                            clip = clip.with_effects([vfx.Rotate(270)])
                            clip = clip.with_effects([vfx.FadeIn(FADEIN_TIME)])
                            clip = clip.with_effects([vfx.FadeOut(FADEOUT_TIME)])
                            # clip = clip.with_effects([vfx.Resize(LAMBDA_EFFECT)])
                            clips.append(clip)

                        elif file_exif.orientation in (1, 8):
                            clips.append(clip.with_duration(TIME).with_effects([vfx.Resize(width=1080), vfx.Rotate(90), vfx.FadeIn(FADEIN_TIME), vfx.FadeOut(FADEOUT_TIME)]))
                        elif file_exif.orientation in (1, 4):
                            clips.append(clip.with_duration(TIME).with_effects([vfx.Resize(width=1080), vfx.Rotate(180), vfx.FadeIn(FADEIN_TIME), vfx.FadeOut(FADEOUT_TIME)]))
                        else:
                            clips.append(clip.with_duration(TIME).with_effects([vfx.FadeIn(FADEIN_TIME), vfx.FadeOut(FADEOUT_TIME)]))
                    except AttributeError:
                        clips.append(clip.with_duration(TIME).with_effects([vfx.FadeIn(FADEIN_TIME), vfx.FadeOut(FADEOUT_TIME)]))
                    except ValueError:
                        clips.append(clip.with_duration(TIME).with_effects([vfx.FadeIn(FADEIN_TIME), vfx.FadeOut(FADEOUT_TIME)]))

                else:
                    clips.append(clip.with_duration(TIME).with_effects([vfx.FadeIn(FADEIN_TIME), vfx.FadeOut(FADEOUT_TIME)]))

        # If video
        if file.endswith(".mp4") or file.endswith(".mov"):
            clip = VideoFileClip(app.config['UPLOAD_FOLDER'] + file)
            clip = clip.with_effects([vfx.Resize(height=HEIGHT_DEFAULT)])
            clip = clip.with_effects([vfx.FadeIn(FADEIN_TIME)])
            clip = clip.with_effects([vfx.FadeOut(FADEOUT_TIME)])
            clips.append(clip)

    video_clip = concatenate_videoclips(clips, method='compose')
    video_clip.write_videofile(PATH_VIDEO_TEMP, fps=24)
    if os.path.exists(PATH_VIDEO):
        os.remove(PATH_VIDEO)
        os.rename(PATH_VIDEO_TEMP, PATH_VIDEO)
    else:
        os.rename(PATH_VIDEO_TEMP, PATH_VIDEO)

    return redirect('/')


def delete_files():
    """
    It will delete the existing files in the user's directory.
    """
    if request.method == 'POST':
        # Check if there's a video with the same name in the static directory
        if os.path.exists(FILES_PATH):
            for filename in os.listdir(FILES_PATH):
                file_path = os.path.join(FILES_PATH, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f'Erro ao deletar {file_path}: {e}')


@app.route('/download')
def download_files():
    """
    It will download the video files in the user's Downloads directory.
    """
    try:
        return send_file(PATH_VIDEO, as_attachment=True)
    except FileNotFoundError:
        return "File not found!", 404


@app.route('/', methods=['GET', 'POST'])
def upload_process_download():
    """
    It will be responsible for identifying which option the user
     is selecting on the system's main page.
    """
    if request.method == 'POST':
        # Check which button was clicked
        if request.form.get('upload'):
            # Call the upload function
            upload_files()
            # Created because the process button wasn't showing up after upload
            time.sleep(1)
            return redirect("/")
        if request.form.get('process'):
            # Call the process function
            process = multiprocessing.Process(target=process_video)
            process.start() # Begin the process execution
            process.join()  # Wait for the process to finish
            return redirect('/')
        if request.form.get('delete'):
            # Call the delete function
            delete_files()
            return redirect('/')

    # Check if video file exist. If yes, the download button will activate
    if os.path.exists(PATH_VIDEO):
        exist_video = 1
    else:
        exist_video = 0

    # Check if the upload file exist. If yes, the process button will activate
    if os.listdir(FILES_PATH) != []:
        exist_file = 1
        # return redirect("/")
    else:
        exist_file = 0

    return render_template('index.html', exist_video=exist_video,
        exist_file=exist_file)


if __name__ == '__main__':
    app.run(debug=True)
