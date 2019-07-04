# Pre Project: Predicting Ship's Motion Based on Machine Learning
***Author:*** [Zhi ZHOU](https://github.com/zroykhi)
# Overview

<div align='center'\>
　　<img src=docs/images/plan.jpg width=600 />
   <br />
   plan
</div>

### Blender simulation

For these first experiments I am using a simple simulation that is only representative of the fact that the boat will respond to sea motion, without looking for physical accuracy or very realistic wave images. I therefore simulated a moving sea with two boats approximated by simple cubes floating on it with a simple physical [model](3dmodel/model.blend). Here are two tutorials about how to set up the [movement](https://www.youtube.com/watch?v=sfi7HW8qHAo) and apply [textures](https://www.youtube.com/watch?v=-GW8jMsQhEU) to objects.

3D simulation in Blender  |  Example of sea surface image generated
:-------------------------:|:-------------------------:
<img src="docs/images/3Dsimulation.png" width="486" />  | ![alt text](docs/images/exampleseaimg.png)

### Data preprocessing

The motion parameters of the ship are collected into a json file in the form of a dictionary, which is an unordered collection of name–value pairs where the names (also called keys, each key is the name of a sea surface image collected) are frame number, and the corresponding value is a list of the ship's motion parameters. As we want to evaluate how long in advance the ship motion prediction has the best performance, we create datasets with different time shifts by associating each image with the value of the image N steps (i.e. frame gap) after, keeping the corresponding parameters of the ship unchanged (see figure below).

Image preprocessing  |  Ship motion param preprocessing
:-------------------------:|:-------------------------:
<img src="docs/images/imgprocessing.png" width="486" />  | <img src="docs/images/datatransform.jpg" width="486" />

### Models

The neural network models I established include CNN with single image as input, CNN with two images as input and the combination of CNN and LSTM. The only difference between convolutional network with one image as input and with two images as input is that the number of channels of input is 6 [R,G,B,R,G,B] instead of 3 [R,G,B].

CNN architecture  |  CNN-LSTM architecture
:-------------------------:|:-------------------------:
<img src="docs/images/cnn-architecture.jpg" width="480" />  | <img src="docs/images/cnn-lstm.jpg" width="480" />

# Project Report & Demo

Project report: [[Google drive]](https://drive.google.com/file/d/1A0Jgqq1ElIiHYhDEImBzrKtDDpGBwnfp/view?usp=sharing) [[Baidu]](https://pan.baidu.com/s/1IRUlwZM_SWJOdQjNbv2OjQ)

Demo video: [[Youtube]](https://youtu.be/zLs0_C_pLLE)

# Acknowledgement
I received a lot of help from M. David Filliat and M. [Antonin RAFFIN](https://github.com/araffin). This work could not be done without their support. Merci beaucoup!

# License

This project is released under a [GPLv3 license](LICENSE).

# Dependencies

 - PyTorch 0.4.0
 - numpy 1.14.5
 - skimage 0.14.0
 - PIL 5.1.0
 - tqdm 4.23.4
 - opencv-python 3.4.1

# Files explanations

`autoRun.sh`: runs all the codes automatically and generates the results. Usage: `bash autoRun.sh` or `sudo bash autoRun.sh` if your python modules is installed with sudo command.

`comparePare.xls`: a xls file which can calculate the parameters of a cnn network if you want to change some of parameters

`constants`: defines some main constants of the project

`models.py`: neural network models

`pltDiff.py`: used to plot figure comparing the original boat parameters and predictions ones

`pltModelTimegap.py`: read the result.txt and plot the model-timeGap-loss figures

`render.py`: used for render images data set with blender file. Run command:
```
blender model.blend --background --python render.py
```
or copy the code to blender's text editor and press "run script"

`result.txt`: contains the results of training (architectures of the network and test loss etc.). Generated automatically by `train.py`

`train.py`: used to train the model

`test.py`: used to predict the results

`transformData.py`: transform the data obtained from `blender.py` to the one which can be used for training

`insertKeyframe.py`: insert the prediction parameters into blender file `model.blend` and visualize the prediction in order to compare with the original ones. Usage: copy the code to blender's text editor and press "run script"

`model.blend`: 3d simulation file, use to generate images dataset

`labels.json`: ground truth data of boat's parameters

# Step guidance:

1. download the code and add environment path by changing the code in `autoRun.sh`

2. download the images dataset [here](https://drive.google.com/file/d/1wf86xezQeI804QpEtDDfxNovNXhN4Y6m/view?usp=sharing) if you have not yet and put the dataset under the directory **3dmodel** (frame 1--5000 are of object "boat", frame 5000--10000 are of object "boat1"), make sure the dataset folder's name is **mixData** and has file **labels.json** inside it. The prediction frame gap is 25 by default.

3. for train, goto Pre's parent folder and run command:
```
python3 -m Pre.train -tf Pre/3dmodel/mixData
```

4. for prediction, goto Pre's parent folder and run command:
```
python3 -m Pre.test -f Pre/3dmodel/mixData
```

5. or you can run autoRun.sh directly

# Some issues

1. After insert keyframes into blender model, the motion postures of the two boats are opposite
```
Make sure that the local coordinates of the two boats are the same, just change them into the same if not (rotate the prediction one)
```
