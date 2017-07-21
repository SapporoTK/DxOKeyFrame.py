# DxOKeyFrame.py #

This is a script to help you create TimeLapse video with DxO OpticsPro(RAW processing software).

You select two keyframe images and this script automatically adjust the intermediate photographs.

When the extended exposure compensation option is turned on, the aperture, shutter speed and ISO at the time of shooting are read, and exposure compensation taking these into consideration is performed.

For example, when taking interval shots in Aperture Priority (A/Av) mode etc., even if there are variations in the apparent shooting result, the exposure compensation will be performed smoothly and continuously.

Video samples and details are here.
https://planet-green.com/dxokeyframe-py/2386 (in Japanese)

Note:
+ It corresponds to parameters other than tone curve.
+ For parameters that can be turned on/off, the setting of the first key frame is applied to all images.
+ Although the operation is confirmed by exposure compensation · color temperature etc., operation check with all parameters is not done.


## Procedure of make time lapse video by this script ##

1. Load the RAW images into DxO OpticsPro.
2. When changed parameter setting in DxO OpticsPro, the setting file whose file name becomes the original file name + .dop is saved in the same directory as the RAW image. This script updates these .dop files.
3. You need the .dop file of all the images. If not, set the parameters of all images by pasting the copied parameter settings to all images.
4. Select the key frame. When the light quantity change is small, there are no problems with only the first and last images. If light intensity suddenly changes in a short time like sunrise or sunset, please select some keyframes.
5. Perform development settings for the selected key frame on DxO OpticsPro.
6. Exit DxO OpticsPro.
6. (**IMPORTANT**) Back up RAW images and .dop files.
7. Execute this script to automatically process the images in the middle of the key frames.
8. Run DxO OpticsPro, check that the parameter settings are normally updated, then export to jpeg or tiff.
9. Convert to a video with video editing software
 or ffmpeg.


## Caution ##
**
Be sure to back up the file before executing it.
Due to bugs in programs and mistakes in operations, not only the .dop file but also the image data itself may be corrupted. **

Also, this script creator has nothing to do with DxO OpticsPro and the developer DxO Labs.
Please do not inquire about this program to DxO Labs.
In addition, the author of this script and DxO Labs are not responsible for any damage caused by this program.


## Recommended system ##
I tested in this environment.
+ DxO OpticsPro 11
+ Mac OS X 10.11.6
+ Python 2.7.x

The camera is confirmed to operate with the RAW file of CANON EOS 5D Mark II. (When extended exposure compensation mode is used).
If you do not use the extended exposure compensation mode, it should work regardless of the model of the camera.

In Windows, processing dependent on Mac OS/Linux is written in function ExitIfExistsDxOProcess(), so probably only there
I think that it will work after change.
(I can not verify it because I am not using Windows)


## Setup ##

 1. Install Python and pip.
 2. Install Libraries.
```bash
pip install exifread
pip install pytz
```


## Usage ##

```bash
python DxOkeyFrame.py [--verbose] [--exposure] [--dry-run] [--help] file1 file2
```
**file1**  
RAW data of the first key frame

**file2**  
RAW data of the last key frame

**--verbose or -v**  
show information

**--exposure or -e**  
Enable extended exposure compensation.
When this mode is enabled, processing time will be longer because the exposure data is read from the RAW file.
Also, there is a possibility that unexpected results may be obtained on models of cameras that the exifread library does not support.

In addition, this option is unnecessary if only the same aperture, shutter speed, and ISO taken with ISO.

**--dry-run or -d**  
Do not update the .dop file, only simulate the process. Please use it when you want to display only calculated results safely.

**--help**  
Show help.


## Example ##
```bash
python DxOkeyFrame.py -v -e /path/to/IMG_0100.CR2 /path/to/IMG_0220.CR2
```  

## Author ##

Author: Tomoya Kawabata   
Home Page: https://planet-green.com/  

## License ##
MIT

-----
Thank you for reading my poor English document to the end.
