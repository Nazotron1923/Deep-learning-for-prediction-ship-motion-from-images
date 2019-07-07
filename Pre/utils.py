from __future__ import print_function, division, absolute_import

import json
import numpy as np
import random
import torch as th
from torch.utils.data import Dataset
from Pre.constants import MAX_WIDTH, MAX_HEIGHT, ROI, INPUT_HEIGHT, INPUT_WIDTH, LEN_SEQ, SEQ_PER_EPISODE_C,  RANDS
from PIL import Image




def gen_dict_for_json(keys, values):
    d = {}
    for i in range(len(values)):
        d [str(keys[i])] = list(np.array(values[i].numpy(), dtype=float))
    return d


def min_max_norm(x, min_e = -90.0, max_e = 90.0):
    return ((x - min_e) * 2) / (max_e - min_e) - 1


def write_result(result_file_name, model_type, best_train_error, best_val_error,
                test_error, time_gap, use_sec, seq_per_ep,
                seq_len, frame_interval, batchsize, randomseed, n_train, n_val,
                n_test, epochs, models : list, optimizers : list, time):
    with open(result_file_name, "a") as f:
        f.write("current model:    ")
        f.write(model_type)
        f.write("\nTraining time:    ")
        f.write(str(time))
        f.write("\nbest train error:    ")
        f.write(str(best_train_error))
        f.write("\nbest validation loss:    ")
        f.write(str(best_val_error))
        f.write("\nfinal test loss:    ")
        f.write(str(test_error))
        f.write("\n")
        f.write("time to predict is (seconds):    ")
        f.write(str(time_gap))
        f.write("\n")
        f.write("time (seconds) used to predict:    ")
        f.write(str(use_sec))
        f.write("\n")
        f.write("Seqences per epizode:    ")
        f.write(str(seq_per_ep))
        f.write("\n")
        f.write("Seqence length:    ")
        f.write(str(seq_len))
        f.write("\n")
        f.write("Frame interval:    ")
        f.write(str(frame_interval))
        f.write("\n")
        f.write("Batch_Size:    ")
        f.write(str(batchsize))
        f.write("\n")
        f.write("Randomseed:    ")
        f.write(str(randomseed))
        f.write("\n")
        f.write("Train examples:    ")
        f.write(str(n_train))
        f.write("\n")
        f.write("Validation examples:    ")
        f.write(str(n_val))
        f.write("\n")
        f.write("Test examples:    ")
        f.write(str(n_test))
        f.write("\n")
        f.write("Epochs:    ")
        f.write(str(epochs))
        for model in models:
            f.write("\n")
            f.write(str(model))

        for optimizer in optimizers:
            f.write("\n")
            f.write(str(optimizer))
        f.write("\n\n--------------------------------------------------------------------------------------------\n\n")
    f.close()


def loadLabels(folder_prefix, N_episodes_st, N_episodes_end, seq_per_ep ,p_train=0.7, p_val=0.15, p_test=0.15):
    random.seed(RANDS)


    all_ep = np.linspace(N_episodes_st*seq_per_ep, N_episodes_end*seq_per_ep, (N_episodes_end*seq_per_ep-N_episodes_st*seq_per_ep +1), dtype =int )

    train_ep = np.array([], dtype =int)
    val_ep = np.array([], dtype =int)
    test_ep = np.array([], dtype =int)

    # TT = int((len(all_ep)*4)/ (N_episodes_end-N_episodes_st))
    TT = int((len(all_ep))/ 60)
    # for min_ep in range(int((N_episodes_end-N_episodes_st)/4)):
    for min_ep in range(60):
        tmp_ep = all_ep[min_ep*TT:(min_ep+1)*TT]
        # tmp_ep = np.linspace(N_episodes_st + tmp*min_ep, N_episodes_st + tmp*(min_ep+1), (tmp +1), dtype =int )
        len_tmp_ep = tmp_ep.size
        random.shuffle(tmp_ep)
        train_ep = np.concatenate((train_ep, tmp_ep[0 : int(p_train*len_tmp_ep)] ))
        val_ep = np.concatenate((val_ep, tmp_ep[int(p_train*len_tmp_ep) : int((p_train+p_val)*len_tmp_ep)] ))
        test_ep = np.concatenate((test_ep, tmp_ep[int((p_train+p_val)*len_tmp_ep): ] ))

    # train_ep = np.concatenate((train_ep,all_ep[int((N_episodes_end-N_episodes_st)/4)*TT:]))
    train_ep = np.concatenate((train_ep,all_ep[60*TT:]))

    random.shuffle(train_ep)
    random.shuffle(val_ep)
    random.shuffle(test_ep)

    return train_ep, val_ep, test_ep



# load train data and test data from different directories
def loadTrainLabels(folder_prefix, modelType, pred_time, N_episodes_st, N_episodes_end, p_train=0.6, p_val=0.2, p_test=0.2):
    random.seed(RANDS)
    all_ep = np.linspace(N_episodes_st, N_episodes_end, (N_episodes_end-N_episodes_st +1), dtype =int )
    # len_all_ep = all_ep.size
    #
    # random.shuffle(all_ep)
    # random.shuffle(all_ep)
    #
    # train_ep = all_ep[0 : int(p_train*len_all_ep)]
    # val_ep = all_ep[int(p_train*len_all_ep) : int((p_train+p_val)*len_all_ep)]
    # test_ep = all_ep[int((p_train+p_val)*len_all_ep): ]


    train_ep = np.array([], dtype =int)
    val_ep = np.array([], dtype =int)
    test_ep = np.array([], dtype =int)
    tmp = int(0.2*(N_episodes_end - N_episodes_st))
    TT = int(len(all_ep)/10)

    for min_ep in range(10):
        tmp_ep = all_ep[min_ep*TT:(min_ep+1)*TT]
        # tmp_ep = np.linspace(N_episodes_st + tmp*min_ep, N_episodes_st + tmp*(min_ep+1), (tmp +1), dtype =int )
        len_tmp_ep = tmp_ep.size
        random.shuffle(tmp_ep)
        train_ep = np.concatenate((train_ep, tmp_ep[0 : int(p_train*len_tmp_ep)] ))
        val_ep = np.concatenate((val_ep, tmp_ep[int(p_train*len_tmp_ep) : int((p_train+p_val)*len_tmp_ep)] ))
        test_ep = np.concatenate((test_ep, tmp_ep[int((p_train+p_val)*len_tmp_ep): ] ))

    train_ep = np.concatenate((train_ep,all_ep[10*TT:]))

    random.shuffle(train_ep)
    random.shuffle(val_ep)
    random.shuffle(test_ep)

    print('train_ep-> ', train_ep)
    print('val_ep-> ', val_ep)
    print('test_ep-> ', test_ep)
    #images = np.array([])



    train_labels = {}
    val_labels = {}
    test_labels = {}

    for episode in train_ep:
        file_name_episode =  folder_prefix  + str(episode) + '/labels_' + str(pred_time) + '.json'
        labels_episode = json.load(open(file_name_episode))
        images_edisode = np.array( list(map(int, list(labels_episode.keys()) )) )
        images_edisode.sort()
        N_images_in_episode = len(labels_episode)
        images_edisode += N_images_in_episode*(episode-1)   # to index every label episode

        #images = np.concatenate([images, images_edisode])
        for l in range(N_images_in_episode*(episode-1), N_images_in_episode*episode):
            train_labels[l] = labels_episode[str(l-N_images_in_episode*(episode-1))]

    for episode in val_ep:
        file_name_episode =  folder_prefix  + str(episode) + '/labels_' + str(pred_time) + '.json'
        labels_episode = json.load(open(file_name_episode))
        images_edisode = np.array( list(map(int, list(labels_episode.keys()) )) )
        images_edisode.sort()
        N_images_in_episode = images_edisode.size
        images_edisode += N_images_in_episode*(episode-1)   # to index every label episode

        #images = np.concatenate([images, images_edisode])
        for l in range(N_images_in_episode*(episode-1), N_images_in_episode*episode):
            val_labels[l] = labels_episode[str(l-N_images_in_episode*(episode-1))]

    for episode in test_ep:
        file_name_episode =  folder_prefix  + str(episode) + '/labels_' + str(pred_time) + '.json'
        labels_episode = json.load(open(file_name_episode))
        images_edisode = np.array( list(map(int, list(labels_episode.keys()) )) )
        images_edisode.sort()
        N_images_in_episode = images_edisode.size
        images_edisode += N_images_in_episode*(episode-1)   # to index every label episode

        #images = np.concatenate([images, images_edisode])
        for l in range(N_images_in_episode*(episode-1), N_images_in_episode*episode):
            test_labels[l] = labels_episode[str(l-N_images_in_episode*(episode-1))]

    return train_labels, val_labels, test_labels

    # load train data and test data from different directories


def loadTestLabels (folder_prefix, pred_time, N_episodes_st, N_episodes_end):
    random.seed(RANDS)
    all_ep = np.linspace(N_episodes_st, N_episodes_end, (N_episodes_end-N_episodes_st +1), dtype =int )
    len_all_ep = all_ep.size

    random.shuffle(all_ep)

    test_ep = all_ep[:]
    print('test_ep-> ', test_ep)

    test_labels = {}

    for episode in test_ep:
        file_name_episode =  folder_prefix  + str(episode) + '/labels_' + str(pred_time) + '.json'
        labels_episode = json.load(open(file_name_episode))
        images_edisode = np.array( list(map(int, list(labels_episode.keys()) )) )
        images_edisode.sort()
        N_images_in_episode = images_edisode.size
        images_edisode += N_images_in_episode*(episode-1)   # to index every label episode

        #images = np.concatenate([images, images_edisode])
        for l in range(N_images_in_episode*(episode-1), N_images_in_episode*episode):
            test_labels[l] = labels_episode[str(l-N_images_in_episode*(episode-1))]

    return test_labels


"""
take N images as input and use data augmentation
"""
class JsonDatasetNIm(Dataset):
    def __init__(self, labels, folder_prefix="", preprocess=False, random_trans=0.0, swap=False, sequence=False, pred_time = 5, frame_interval = 12, N_im = 2, mean = [0.5, 0.5, 0.5] , std = [0.5, 0.5 , 0.5]):
        self.keys = list(labels.keys())
        self.sequence = sequence
        self.labels = labels.copy()
        self.folder_prefix = folder_prefix
        self.preprocess = preprocess
        self.random_trans = random_trans
        self.swap = swap
        self.frame_interval = frame_interval
        self.numChannel = 3*N_im
        self.N_im = N_im
        self.pred_time = pred_time
        self.mean = mean
        self.std = std
        if self.sequence:
            self.keys.sort()


    def __getitem__(self, index):
        """
        :param index: (int)
        :return: (PyTorch Tensor, PyTorch Tensor)
        """
        # Through the division of the data into episodes, it is necessary to use labels's index
        index = self.keys[index]
        time_ordered_images = []
        # Get labels for input images
        labels = np.array(self.labels[index]).astype(np.float32)
        y = labels.flatten().astype(np.float32)

        # to correctly determine the location of images in episodes
        tmp = 400 - int (24/self.frame_interval) * self.pred_time
        episode = index//tmp + 1
        image = index - tmp*(episode-1)

        # to form a mini_time_series we nneed N images
        # But for (N-1) first images there is no full series
        # So we will not use such incomplete series to no degrade the performance
        if((image - self.N_im+1) < 0):
            print("index_ ", index)
            print("image_ ", image )
            print("self.N_im_ ", self.N_im)
            return th.zeros(self.numChannel, 54, 96, dtype = th.float32 ), th.zeros(2, dtype = th.float32 )


        for i in range(self.N_im):
            # maybe need to inverse (image - self.N_im + i)
            image_str = str(image-i) + ".png"
            margin_left, margin_top = 0, 0
            # im = cv2.imread(self.folder + image) # BGR(270, 486, 3)
            file = self.folder_prefix + str(episode) + '/' + image_str
            im = Image.open(file).convert("RGB") # RGB(270, 486, 3)
            im = np.asarray(im)
            im = im.astype('float')
            # print('im --', im.shape)
            # normalize it
            if self.preprocess:
                for canal in range(3):
                    im[...,canal] = (im[...,canal]*2)/255 - 1

            time_ordered_images.append(im)
        time_ordered_images = np.dstack(time_ordered_images)
        # swap color axis because
        # numpy image: H x W x C
        # torch image: C X H X W
        time_ordered_images = time_ordered_images.transpose((2, 0, 1)).astype(np.float32)
        return th.from_numpy(time_ordered_images), th.from_numpy(y)

    def __len__(self):
        return len(self.keys)


"""
description to add
"""
class JsonDataset_universal (Dataset):
    def __init__(self, labels, folder_prefix="", preprocess=False, predict_n_im = 10, use_n_im = 10, seq_per_ep = 36, use_LSTM = False, use_stack = False):
        self.keys = labels.copy()
        self.folder_prefix = folder_prefix
        self.preprocess = preprocess
        self.predict_n_im = predict_n_im
        self.use_n_im = use_n_im
        self.seq_per_ep = seq_per_ep
        self.use_LSTM = use_LSTM
        self.use_stack = use_stack

    def __getitem__(self, index):
        """
        :param index: (int)
        :return: (PyTorch Tensor, PyTorch Tensor)
        """
        # Through the division of the data into episodes, it is necessary to use labels's index
        index = self.keys[index]
        seq_images = []
        seq_labels = []
        if not self.use_LSTM:
            seq_future = []

        # To find photo position
        episode = index//self.seq_per_ep + 1
        seq_in_episodes = index%self.seq_per_ep + 1

        file_name =  self.folder_prefix  + str(episode) + '/labels_0.json'
        labels_episode = json.load(open(file_name))
        # min_max_stat = json.load(open("Pre/3dmodel/min_max_statistic_320.json"))

        tmp_use_n_im = self.use_n_im
        if self.use_LSTM:
            tmp_use_n_im =  LEN_SEQ

        for i in range(tmp_use_n_im):
            image = (seq_in_episodes-1)*tmp_use_n_im + i
            # maybe need to inverse (image - self.N_im + i)
            image_str = str(image) + ".png"

            file = self.folder_prefix + str(episode) + '/' + image_str
            im = Image.open(file).convert("RGB") # RGB(270, 486, 3)
            im = np.asarray(im)
            im = im.astype('float')

            tmp_label = np.array(labels_episode[str(image)])

            # normalize it
            if self.preprocess:
                for chanal in range(3):
                    im[...,chanal] = (im[...,chanal]*2)/255 - 1

                tmp_label[0] = min_max_norm(tmp_label[0])
                tmp_label[1] = min_max_norm(tmp_label[1])

            seq_images.append(im)
            seq_labels.append(tmp_label)


        seq_labels = np.array(seq_labels, dtype = np.float32)

        # swap color axis because
        # numpy image: H x W x C
        # torch image: C X H X W
        if self.use_stack:
            seq_images = np.dstack(seq_images)
            seq_images = np.array(seq_images, dtype = np.float32)
            seq_images = seq_images.transpose((2, 0, 1)).astype(np.float32)
        else:
            seq_images = np.array(seq_images, dtype = np.float32)
            seq_images = seq_images.transpose((0, 3, 1, 2)).astype(np.float32)



        if not self.use_LSTM:
            for i in range(self.predict_n_im):
                image = (seq_in_episodes-1)*tmp_use_n_im + tmp_use_n_im + i
                tmp_label_future = np.array(labels_episode[str(image)])

                # normalize it
                if self.preprocess:
                    tmp_label_future[0] = min_max_norm(tmp_label_future[0])
                    tmp_label_future[1] = min_max_norm(tmp_label_future[1])

                seq_future.append(tmp_label_future)

            seq_future = np.array(seq_future, dtype = np.float32)


        if not self.use_LSTM:
            return th.from_numpy(seq_images), th.from_numpy(seq_labels), th.from_numpy(seq_future)
        else:
            return th.from_numpy(seq_images), th.from_numpy(seq_labels)

    def __len__(self):
        return len(self.keys)
