# DxOKeyFrame.py #

## 概要 ##
RAW現像ソフトのDxO OpticsProでTimeLapse(タイムラプス、微速度撮影)動画制作を支援するスクリプトです。

従来だと、例えば100枚の写真をインターバル撮影して、動画にした時に光量変化が滑らかになるように露出補正するためには、RAW現像ソフトで100枚を手動で調整する必要がありました。

このスクリプトを使うと、調整する必要があるのは最初と最後の2枚だけで、後は自動的に中間の写真の現像設定を行います。

また、拡張露出補正オプションをオンにすると、撮影時の絞り・シャッター速度・ISO感度を読み込み、それらを考慮した露出補正を行います。

これは例えば、絞り優先（A/Av）モードなどでインターバル撮影して、見かけの撮影結果に露出のばらつきがあっても、滑らかに連続するように露出補正してくれます。

動画サンプルと詳細はこちら。
https://planet-green.com/dxokeyframe-py/2386

## 注意 ##
**実行する前に必ずファイルのバックアップを取ってください。  
プログラムのバグ、あるいは操作のミスで、.dopファイルだけでなく、画像データそのものが壊れる可能性があります。**

このプログラムは、元々は私が個人的に趣味で使うために作ったものです。  
そのため、厳密な動作テストや検証を行っていません。
それを理解していただける方のみ、利用してください。

また、本プログラムと制作者は、はDxO OpticsPro及び開発元のDxO Labsとは一切の関係がありません。
本プログラムに関する問い合わせをDxO Labsにしないでください。
また、本プログラムが原因で生じたいかなる損害も、本ソフトの作者およびDxO Labsは一切責任を負いません。


## 推奨システム ##
下記の環境で動作確認しています。それ以外の環境については、動作報告していただけると嬉しいです。
+ DxO OpticsPro 11
+ Mac OS X 10.11.6
+ Python 2.7.x

カメラは、CANON EOS 5D Mark IIのRAWファイルで動作確認しています。(拡張露出補正モードを使用する場合)。
拡張露出補正モードを使用しない場合は、カメラの機種に関係なく動作するはずです。


## セットアップ

 1. Pythonとpipのインストール。
 2. ライブラリのインストール。
 ```bash
pip install exifread
pip install pytz
```

## 使用法 ##

DxO OpticsProの終了後、ターミナル(コマンドプロンプト)から実行します。

```bash
python DxOkeyFrame.py [--verbose] [--exposure] [--dry-run] [--help] file1 file2
```
**file1**  
先頭キーフレームのRAWデータのパス。

**file2**  
最後のキーフレームのRAWデータのパス。

**--verbose or -v**  
途中経過を詳細に表示する。  

**--exposure or -e**  
拡張露出補正モードを有効にする。このモードを有効にするとRAWファイルから露出データを読み込むため、処理時間が長くなります。  
また、exifreadライブラリが対応していないカメラの機種では予期しない結果になる可能性があります。  
尚、同じ絞り・シャッター速度・ISOで撮影した写真だけならばこのオプションは不要です。

**--dry-run or -d**  
.dopファイルは書き換えずに、処理のシミュレーションだけを実行します。安全に計算結果だけを確認したい場合などに利用してください。  

**--help**  
ヘルプメッセージを表示する。  


### 使用例 ###
```bash
python DxOkeyFrame.py -v -e /path/to/IMG_0100.CR2 /path/to/IMG_0220.CR2
```  

この例では IMG_0100.CR2 から IMG_0220.CR2までの121枚を処理します。



## Author ##

Author: Tomoya Kawabata   
Home Page: https://planet-green.com/  

## License ##
MIT
