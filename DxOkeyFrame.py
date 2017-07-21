#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DxOKeyFrame.py Ver 1.0
Copyright (C) 2017 Tomoya Kawabata (https://planet-green.com/)


This script is released under the MIT License:https://opensource.org/licenses/MIT

-----------------------------------------------------------------------
The MIT License (MIT)

Copyright 2017 Tomoya Kawabata

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
-----------------------------------------------------------------------
"""


import sys
import signal
import re
import json
import math
import os
import fcntl
import datetime
import commands
import exifread

from argparse import ArgumentParser
from datetime import datetime
from pytz import timezone


global_is_now_safe_exit = True
global_kill_now = False

def signalHandler(signal, frame):
    global global_is_now_safe_exit
    global global_kill_now

    if global_is_now_safe_exit:
        interrupt()
    else:
        global_kill_now = True

def interrupt():
    print ""
    sys.exit(0)

signal.signal(signal.SIGINT,  signalHandler)
signal.signal(signal.SIGTERM, signalHandler)


def ExitIfExistsDxOProcess():
    result = commands.getoutput( 'ps ax | grep DXOOptics | grep -v grep')
    if "DXOOptics" in result:
        print "Please Terminate DxO Optics."
        sys.exit()


def getExif(fname):

    f = open(fname, 'rb')
    tags = exifread.process_file(f)

    expo_str = tags.get("EXIF ExposureTime").printable
    aprt_str = tags.get("EXIF FNumber").printable
    iso = float(tags.get("EXIF ISOSpeedRatings").printable)

    m = re.search( "^(\d+)\/(\d+)$", expo_str )

    if m:
        expo = round( float(m.group(1)) / float(m.group(2)), 6)
    else :
        expo = round( float(expo_str) )

    m = re.search( "^(\d+)\/(\d+)$", aprt_str)

    if m:
        aprt = round( float(m.group(1)) / float(m.group(2)), 2)
    else :
        aprt = round( float(aprt_str), 2)

    return {"t":expo, "f":aprt, "iso":iso}


def parseDopData(allLines):

    #.dopファイルは独自のフォーマットであるが少し修正するだけでJSONとしてパースできる。

    #末尾の不要なコンマ
    #   コンマの後に} が続いているパターンで検出
    allLines = re.sub( r',(\s*)}', r'\1}', allLines, flags=(re.MULTILINE | re.DOTALL))

    # 数字だけが列挙された(キーの無い値だけの)配列は [] に
    allLines = re.sub( r'{([ \t\r\n0-9,.]+)}', r'[\1]', allLines, flags=(re.MULTILINE | re.DOTALL))

    listAllLines = list(allLines)

    #　波括弧が2回続いていたら外側を角括弧に。 { { -> [ {
    iterator = re.finditer( r'{(\s*){', allLines, flags=(re.MULTILINE | re.DOTALL))

    # 閉じ角括弧を探して置換
    for match in iterator:
        listAllLines[match.start()] = "["

        n = 1
        p = match.start()
        strlen = len(allLines)
        while n > 0 and (p + 1) < strlen:
            p += 1
            # print listAllLines[p] + ","
            if ( listAllLines[p] == '}'): n -= 1
            if ( listAllLines[p] == '{'): n += 1
        listAllLines[p] = "]"

    allLines = ''.join(listAllLines)

    # abc = def -> "abc":"def"
    allLines = re.sub( r'([A-Za-z0-9]+) = ', r'"\1":', allLines, flags=(re.MULTILINE | re.DOTALL))

    data = json.loads( "{" + allLines + "}")

    #要素数が0だった時に辞書でなくlistと認識されてしまうので明示的に辞書にする。
    if( len(data["Sidecar"]["Source"]["Items"][0]["Settings"]["Overrides"]) == 0 ):
        data["Sidecar"]["Source"]["Items"][0]["Settings"]["Overrides"] = {}

    return data


def dataToDopData(data):
    str = json.dumps(data, indent=1, separators=(',', ' = '), sort_keys=True)

    #スペースをタブに変換
    str = re.sub( '\n +', lambda match: '\n' + '\t' * len(match.group().strip('\n')), str)

    # クォートを取り除く
    str = re.sub( r'\"([a-zA-Z0-9_]+)\" = ', r'\1 = ', str)

    #角括弧を波括弧に
    str = str.replace('[', '{').replace(']', '}')

    #外側の波括弧を削除
    str = str[1:len(str)-1]

    #全体を1タブ下げ
    str = re.sub( '^\t', '', str, flags=(re.MULTILINE | re.DOTALL) )

    return str


def exposureValue(f, t, iso):
    return (1 / f**2) * t * (iso/100)


# 最初のフレームと最後のフレームの、露光量+露光補正(ExposureBias)を求める
def totalExposureValue(f, t, iso, ExposureBias):

    ev = exposureValue(f, t, iso)
    return ev * (2**ExposureBias)


# 露光補正量を求める。各フレーム用。
def calcExposureBias(f, t, iso, totalExposureValue):

    ev = exposureValue(f, t, iso)
    bias = math.log( totalExposureValue / ev, 2)

    if( bias > 4.0):
        bias = 4.0

    if( bias < -4.0 ):
        bias = -4.0

    return bias


def main():

    global global_is_now_safe_exit
    global global_kill_now

    #
    # get params
    #
    usage = 'python {} [--verbose] [--exposure] [--dry-run] [--help] file1 file2'.format(__file__)

    if( len(sys.argv) == 1 ):
        print usage
        sys.exit()

    argparser = ArgumentParser(usage=usage)

    argparser.add_argument('file1', type=str, help='start key file', nargs='?')
    argparser.add_argument('file2', type=str, help='end key file', nargs='?')

    argparser.add_argument('-v', '--verbose',  action="store_true", help='show verbose message')
    argparser.add_argument('-e', '--exposure',  action="store_true", help='extend exposure value mode')
    argparser.add_argument('-d', '--dry-run', action='store_true', help='simulation only.', dest='dry' )

    args = argparser.parse_args()

    fname1 = args.file1
    fname2 = args.file2
    flg_verbose = args.verbose
    flg_exposure = args.exposure
    flg_dryRun = args.dry

    if (fname1 is None or fname1 == "" or not os.path.isfile(fname1) ):
        print "ERROR(file1)"
        sys.exit()

    if (fname2 is None or fname2 == "" or not os.path.isfile(fname2) ):
        print "ERROR(file2)"
        sys.exit()

    file_dir = os.path.dirname(fname1)

    if( file_dir != os.path.dirname(fname2) ) :
        print "ERROR(The dir of file1 and file2 are different)"
        sys.exit()

    file_dir = file_dir + ( "" if file_dir=="" else "/" )

    fname1 = os.path.basename(fname1)
    fname2 = os.path.basename(fname2)

    # RAWファイル名をパース
    m = re.search( "^([a-zA-Z_\-]*)(\d+)([a-zA-Z0-9_\-]*)\.([a-zA-Z0-9_\-]+)$", fname1)

    if m:
        fname_prefix = m.group(1)   # e.g. "IMG_"
        fname_suffix = m.group(3)
        fname_ext = m.group(4)
        file_num_start = int(m.group(2))
    else :
        print "ERROR(parse file name 1)"
        sys.exit()

    m = re.search( "^([a-zA-Z_\-]*)(\d+)([a-zA-Z0-9_\-]*)\.([a-zA-Z0-9_\-]+)$", fname2)

    if m:
        file_num_end = int(m.group(2))
    else :
        print "ERROR(parse file name 2)"
        sys.exit()

    total_num = file_num_end - file_num_start

    if total_num < 2 :
        print "ERROR(file count)"
        sys.exit()

    if not flg_dryRun:
        ExitIfExistsDxOProcess()



    text = open( file_dir + fname1 + ".dop" ).read()
    data_start = parseDopData(text)

    text = open( file_dir + fname2 + ".dop" ).read()
    data_end = parseDopData(text)

    setting_st_bs = data_start["Sidecar"]["Source"]["Items"][0]["Settings"]["Base"]
    setting_st_ov = data_start["Sidecar"]["Source"]["Items"][0]["Settings"]["Overrides"]

    setting_en_bs = data_end["Sidecar"]["Source"]["Items"][0]["Settings"]["Base"]
    setting_en_ov = data_end["Sidecar"]["Source"]["Items"][0]["Settings"]["Overrides"]


    #整数の値を持つパラメーター
    params_int = [
        "AnamorphosisHorizontal",
        "AnamorphosisRadial",
        "AnamorphosisVertical",
        "ArtisticVignettingCornerAttenuation",
        "ArtisticVignettingMidFieldAttenuation",
        "ArtisticVignettingRoundness",
        "ArtisticVignettingTransition",
        "ChannelMixerBlue",
        "ChannelMixerCyan",
        "ChannelMixerGreen",
        "ChannelMixerMagenta",
        "ChannelMixerRed",
        "ChannelMixerYellow",
        "ChromaticAberrationIntensity",
        "ChromaticAberrationSize",
        "ColorModeContrast",
        "ColorModeFilterIntensity",
        "ContrastEnhancementGlobalIntensity",
        "ContrastEnhancementHighlightIntensity",
        "ContrastEnhancementLowlightIntensity",
        "ContrastEnhancementMidlightIntensity",
        "CropRatio",
        "DehazingValue",
        "DistortionIntensity",
        "DistortionFocus",
        "EdgeTexturingSeed",
        "FramingSeed",
        "GrainIntensity",
        "GrainSize",
        "HighlightToningIntensity",
        "KeystoningBlendingIntensity",
        "KeystoningHVRatio",
        "KeystoningHorizon",
        "KeystoningLeftRight",
        "KeystoningUpDown",
        "LightingBlackPoint",
        "LightingContrastGlobal",
        "LightingContrastLocal",
        "LightingGamma",
        "LightingIntensity",
        "LightingRadius",
        "LightingShadowPreservation",
        "LightingV2BlackPoint",
        "LightingV2BrightnessAmount",
        "LightingV2HiLightsGain",
        "LightingV2Intensity",
        "LightingV2LoLightsGain",
        "LightingV2LocalContrastAmount",
        "LightingV3BlackPoint",
        "LightingV3Highlights",
        "LightingV3MidTones",
        "LightingV3Shadows",
        "LightingV3WhitePoint",
        "LightingWhitePoint",
        "LowlightToningIntensity",
        "MultiPointColorBalanceIntensity",
        "OutputImageMaxSize",
        "TexturingSeed",
        "TiltShiftActive",
        "ToneCurveBlueGamma",
        "ToneCurveGreenGamma",
        "ToneCurveMasterGamma",
        "ToneCurveRedGamma",
        "UnsharpMaskThreshold",
        "VignettedBlurBlendFactor",
        "VignettedBlurRadius",
        "VignettedBlurRoundness",
        "VignettedBlurTransition",
        "VignettedBlurVignetteSize",
        "VignettingClipping",
        "VignettingMidFieldIntensity",
        "WhiteBalanceRGBTemperature"
    ]

    #小数の値を持つパラメーター
    params_float = [
        "BlurDetails",
        "BlurIntensity",
        "BlurSmoothTransitions",
        "ColorModeContrast",
        "ColorModeStyleIntensity",
        "ColorRenderingIntensity",
        "ColorRenderingIntent",
        "EdgeTexturingOpacity",
        "ExposureBias",
        "FramingScaleFactor",
        "HighlighsLowlightsSeparation",
        "HSLBlueHue",
        "HSLBlueLuminance",
        "HSLBlueSaturation",
        "HSLCyanHue",
        "HSLCyanLuminance",
        "HSLCyanSaturation",
        "HSLGreenHue",
        "HSLGreenLuminance",
        "HSLGreenSaturation",
        "HSLMagentaHue",
        "HSLMagentaLuminance",
        "HSLMagentaSaturation",
        "HSLMasterHue",
        "HSLMasterLuminance",
        "HSLMasterSaturation",
        "HSLRedHue",
        "HSLRedLuminance",
        "HSLRedSaturation",
        "HSLYellowHue",
        "HSLYellowLuminance",
        "HSLYellowSaturation",
        "KeystoningHorizon",
        "LightingV3Intensity",
        "NoiseChrominance",
        "NoiseDeadPixelIntensity",
        "NoiseLuminance",
        "NoiseLuminanceContrast",
        "NoiseRemoveMoireIntensity",
        "UnsharpMaskIntensity",
        "UnsharpMaskIntensityOffset",
        "UnsharpMaskRadius",
        "UnsharpMaskThreshold",
        "TexturingOpacity",
        "UnsharpMaskRadius",
        "VignettingIntensity",
        "VibrancyIntensity",
        "WhiteBalanceRawTemperature",
        "WhiteBalanceRawTint"
    ]

    #値が数値でないパラメーター
    params_fix = [
    	"ColorRenderingType",
    	"NoiseRemovalMethod",
    ]

    diffs = {}
    values_start = {}
    values_end = {}
    values_fix = {}

    for key in (params_int + params_float):

        if( ( setting_st_ov.has_key(key) or setting_st_bs.has_key(key)) and ( setting_en_ov.has_key(key) or setting_en_bs.has_key(key)) ):
            value_st = float( setting_st_ov.get(key, setting_st_bs.get(key,0)) )
            value_en = float( setting_en_ov.get(key, setting_en_bs.get(key,0)) )
            values_start[key] = value_st
            values_end[key] = value_en
            diffs[key] = value_en - value_st
        else:
            try:
                params_int.remove(key)
            except ValueError:
                pass

            try:
                params_float.remove(key)
            except ValueError:
                pass

            print "del: " + key

    #カラーレンダリング設定など、1枚目の設定を以降の全ての画像に適用するパラメーター
    for key in (params_fix):
    	if( setting_st_ov.has_key(key) or setting_st_bs.has_key(key) ):
    		values_fix[key] = setting_st_ov.get(key, setting_st_bs.get(key,0))
    	else:
    		try:
              		params_fix.remove(key)
    	        except ValueError:
    			pass

    exif_st = getExif(fname1)
    exif_en = getExif(fname2)

    tExpV_st = totalExposureValue(exif_st["f"], exif_st["t"], exif_st["iso"], values_start["ExposureBias"])
    tExpV_en = totalExposureValue(exif_en["f"], exif_en["t"], exif_en["iso"], values_end["ExposureBias"])
    tExpV_diff = tExpV_en - tExpV_st

    if flg_verbose:
        print 'Start Frame EV F:%02.1f T:%02.6f ISO:%d tEV:%f' % (exif_st["f"], exif_st["t"], exif_st["iso"], tExpV_st)
        print 'End   Frame EV F:%02.1f T:%02.6f ISO:%d tEV:%f' % (exif_en["f"], exif_en["t"], exif_en["iso"], tExpV_en)

    #
    #	main loop
    #
    i = 1
    for file_number in range( (file_num_start+1), (file_num_end) ):
        formatted_num = '%04d' % file_number
        cur_filename_raw = file_dir + fname_prefix + formatted_num + fname_suffix + "." + fname_ext
        cur_filename_dop = cur_filename_raw + ".dop"

        if not os.path.isfile(cur_filename_dop):
            print "ERROR(file not found: " + cur_filename_dop + ")"
            sys.exit()

        if flg_dryRun:
            file_open_mode = 'r'
        else:
            file_open_mode = 'r+'

        with open( cur_filename_dop, file_open_mode) as f:

            if flg_verbose:
                print cur_filename_dop + ":"
            else:
                sys.stdout.write("+")

            try:
                fcntl.flock(f, fcntl.LOCK_EX)
            except IOError:
                print('ERRO(file lock)')
                sys.exit()

            text = f.read()
            data = parseDopData(text)

            date_str = datetime.now(timezone('UTC')).strftime('%Y-%m-%dT%H:%M:%SZ')
            data["Sidecar"]["Date"] = date_str
            data["Sidecar"]["Source"]["Items"][0]["ModificationDate"] = date_str

            setting_bs = data["Sidecar"]["Source"]["Items"][0]["Settings"]["Base"]
            setting_ov = data["Sidecar"]["Source"]["Items"][0]["Settings"]["Overrides"]

            percent = float(i) / float(total_num)

            for key in params_int:
                setting_ov[key] = round(values_start[key] + diffs[key] * percent)
                if( setting_ov[key] == setting_bs.get(key, False) ) :
                    del setting_ov[key]
                else :
                    if flg_verbose:
                        print "\t" + key + " : " + ('%d' % setting_ov[key])

            for key in params_float:
                setting_ov[key] = round(values_start[key] + diffs[key] * percent, 6)
                if( setting_ov[key] == setting_bs.get(key, False) ) :
                    del setting_ov[key]
                else :
                    if flg_verbose:
                        print "\t" + key + " : " + ('%f' % setting_ov[key])

        	for key in params_fix:
        		setting_ov[key] = values_fix[key]

            if(flg_exposure) :
                exif = getExif(cur_filename_raw)
                curExposureValue = tExpV_st + tExpV_diff * percent
                setting_ov["ExposureBias"] = calcExposureBias(exif["f"], exif["t"], exif["iso"], curExposureValue)
                if flg_verbose:
                    print '\tF:%02.1f T:%02.6f ISO:%d' % (exif["f"], exif["t"], exif["iso"])
                    print '\tcurExposureValue:%f' %  curExposureValue
                    print "\tExposureBias(override) : " + ('%f' % setting_ov["ExposureBias"])

            text = dataToDopData(data)

            if(not flg_dryRun) :
                # update .dop file
                global_is_now_safe_exit = False
                f.truncate(0)
                f.seek(os.SEEK_SET)
                f.write(text)

            f.close()

            global_is_now_safe_exit = True
            if global_kill_now:
                interrupt()

        i += 1

        if flg_verbose:
            print ""

        sys.stdout.flush()

    print ""
    print "done.\n"
    sys.exit()


if __name__ == '__main__':
    main()
