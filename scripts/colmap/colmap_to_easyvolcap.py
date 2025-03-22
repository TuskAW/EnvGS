"""
Convert COLMAP format camera parameters to EasyVolcap
Also link all images in their respective folders
Compared to colmap_to_easymocap.py, this script has a better commandline interface
"""
import cv2
from easyvolcap.utils.console_utils import *

from easyvolcap.utils.easy_utils import write_camera
from easyvolcap.utils.colmap_utils import qvec2rotmat, read_model, read_cameras_text, read_images_text, detect_model_format, read_cameras_binary, read_images_binary


def detect_model_format(path, ext):
    if os.path.isfile(os.path.join(path, "cameras" + ext)) and \
       os.path.isfile(os.path.join(path, "images" + ext)):
        print("Detected model format: '" + ext + "'")
        return True

    return False


@catch_throw
def main():
    args = dotdict(
        data_root='data/bullet/final',
        colmap='bkgd/colmap/colmap_sparse/0',
        output='',
        sub='',
        scale=1.0,
    )
    args = dotdict(vars(build_parser(args, description=__doc__).parse_args()))
    args.colmap = join(args.data_root, args.colmap)
    args.output = join(args.data_root, args.output)

    # cameras, images, points3D = read_model(path=args.colmap)
    ext = ''
    if ext == "":
        if detect_model_format(args.colmap, ".bin"):
            ext = ".bin"
        elif detect_model_format(args.colmap, ".txt"):
            ext = ".txt"
        else:
            print("Provide model format: '.bin' or '.txt'")
            return

    if ext == '.bin':
        cameras = read_cameras_binary(join(args.colmap, "cameras" + ext))
        images = read_images_binary(join(args.colmap, "images" + ext))
    else:
        cameras = read_cameras_text(join(args.colmap, "cameras" + ext))
        images = read_images_text(join(args.colmap, "images" + ext))
    log(f"number of cameras: {len(cameras)}")
    log(f"number of images: {len(images)}")
    # log(f"number of points3D: {len(points3D)}")

    intrinsics = {}
    for key in cameras.keys():
        p = cameras[key].params
        if cameras[key].model == 'SIMPLE_RADIAL':
            f, cx, cy, k = p
            K = np.array([f, 0, cx, 0, f, cy, 0, 0, 1]).reshape(3, 3)
            dist = np.array([[k, 0, 0, 0, 0]])
        elif cameras[key].model == 'PINHOLE':
            K = np.array([[p[0], 0, p[2], 0, p[1], p[3], 0, 0, 1]]).reshape(3, 3)
            dist = np.array([[0., 0., 0., 0., 0.]])
        else:  # OPENCV
            K = np.array([[p[0], 0, p[2], 0, p[1], p[3], 0, 0, 1]]).reshape(3, 3)
            dist = np.array([[p[4], p[5], p[6], p[7], 0.]])
        H, W = cameras[key].height, cameras[key].width
        intrinsics[key] = {'K': K, 'dist': dist, 'H': H, 'W': W}

    easycams = {}
    for key, val in sorted(images.items(), key=lambda item: item[0]):
        if args.sub in val.name:
            log(f'preparing camera: {val.name}(#{val.camera_id})')
            cam = intrinsics[val.camera_id].copy()
            t = val.tvec.reshape(3, 1)
            R = qvec2rotmat(val.qvec)
            cam['Rvec'] = cv2.Rodrigues(R)[0]
            cam['R'] = R
            cam['T'] = t * args.scale
            easycams[os.path.splitext(os.path.basename(val.name))[0]] = cam
            # easycams[f"{int(os.path.splitext(os.path.basename(val.name))[0]) - 1:04d}"] = cam
        else:
            log(f'skipping camera: {val.name}(#{val.camera_id}) since {args.sub} not in {val.name}', 'yellow')

    # Dicts preserve insertion order in Python 3.7+. Same in CPython 3.6, but it's an implementation detail.
    easycams = dict(sorted(easycams.items(), key=lambda item: item[0]))
    write_camera(easycams, args.output)

if __name__ == '__main__':
    main()