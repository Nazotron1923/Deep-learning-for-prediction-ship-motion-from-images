"""
Train a neural network to predict vessel's movement
"""
from __future__ import print_function, division, absolute_import

import argparse
import time
import json
import os
from datetime import datetime
import random
import numpy as np
import torch as th
import torch.utils.data
import torch.nn as nn
from torch.autograd import Variable

from Pre.constants import SEQ_PER_EPISODE_C, LEN_SEQ, RES_DIR
# run this code under ssh mode, you need to add the following two lines codes.
# import matplotlib
# matplotlib.use('Agg')
from Pre.utils import loadLabels, gen_dict_for_json, write_result, use_pretrainted

from Pre.utils import JsonDataset_universal as JsonDataset
from Pre.earlyStopping import EarlyStopping
from Pre.models import CNN_stack_FC_first, CNN_stack_FC, CNN_stack_PR_FC, CNN_LSTM_encoder_decoder_images_PR, AutoEncoder, LSTM_encoder_decoder_PR, CNN_LSTM_encoder_decoder_images, CNN_LSTM_decoder_images_PR, CNN_PR_FC, CNN_LSTM_image_encoder_PR_encoder_decoder

"""if above line didn't work, use following two lines instead"""
import matplotlib.pyplot as plt
plt.switch_backend('agg')
from tqdm import tqdm
from torchvision import transforms
from Pre.get_hyperparameters_configuration import get_params

import scipy.misc
from Pre.hyperband import Hyperband

def train(inputs, targets, model, optimizer, criterion, predict_n_pr, use_n_im, use_2_encoders = False):

    if not use_2_encoders:
        encoder_hidden = (model.initHiddenEncoder(inputs.size(0)).cuda(),
                    model.initHiddenEncoder(inputs.size(0)).cuda())
    else:
        im_encoder_hidden = (model.initHiddenEncoderIm(inputs.size(0)).cuda(),
                    model.initHiddenEncoderIm(inputs.size(0)).cuda())
        pr_encoder_hidden = (model.initHiddenEncoderPR(inputs.size(0)).cuda(),
                    model.initHiddenEncoderPR(inputs.size(0)).cuda())

    decoder_hidden = (model.initHiddenDecoder(targets.size(0)).cuda(),
                    model.initHiddenDecoder(targets.size(0)).cuda())

    optimizer.zero_grad()

    target_length = LEN_SEQ - predict_n_pr - use_n_im
    loss = 0

    for im in range(use_n_im-1, target_length+use_n_im):

        image_s = [inputs[:,im-i,:,:,:] for i in range(use_n_im - 1, -1, -1)]
        pr_s = [targets[:,im-i,:] for i in range(use_n_im - 1, -1, -1)]


        if not use_2_encoders:
            prediction, encoder_hidden, decoder_hidden = model(image_s, pr_s, use_n_im, predict_n_pr, encoder_hidden, decoder_hidden)
        else:
            prediction, im_encoder_hidden, pr_encoder_hidden, decoder_hidden = model(image_s, pr_s, use_n_im, predict_n_pr, im_encoder_hidden, pr_encoder_hidden, decoder_hidden)

        loss += criterion(prediction, targets[:,im+1 : im+predict_n_pr+1,:])/predict_n_pr


    loss.backward()
    optimizer.step()

    return loss.item() / target_length


def eval(inputs, targets, model, criterion, predict_n_pr, use_n_im, use_2_encoders = False):

    if not use_2_encoders:
        encoder_hidden = (model.initHiddenEncoder(inputs.size(0)).cuda(),
                    model.initHiddenEncoder(inputs.size(0)).cuda())
    else:
        im_encoder_hidden = (model.initHiddenEncoderIm(inputs.size(0)).cuda(),
                    model.initHiddenEncoderIm(inputs.size(0)).cuda())
        pr_encoder_hidden = (model.initHiddenEncoderPR(inputs.size(0)).cuda(),
                    model.initHiddenEncoderPR(inputs.size(0)).cuda())

    decoder_hidden = (model.initHiddenDecoder(targets.size(0)).cuda(),
                    model.initHiddenDecoder(targets.size(0)).cuda())

    target_length = LEN_SEQ - predict_n_pr - use_n_im

    with th.no_grad():
        loss = 0

        for im in range(use_n_im-1, target_length+use_n_im):

            image_s = [inputs[:,im-i,:,:,:] for i in range(use_n_im - 1, -1, -1)]
            pr_s = [targets[:,im-i,:] for i in range(use_n_im - 1, -1, -1)]

            if not use_2_encoders:
                prediction, encoder_hidden, decoder_hidden = model(image_s, pr_s, use_n_im, predict_n_pr, encoder_hidden, decoder_hidden)
            else:
                prediction, im_encoder_hidden, pr_encoder_hidden, decoder_hidden = model(image_s, pr_s, use_n_im, predict_n_pr, im_encoder_hidden, pr_encoder_hidden, decoder_hidden)

            loss += criterion(prediction, targets[:,im+1:im+predict_n_pr+1,:])/predict_n_pr

    return loss.item() / target_length


def test(i, origins, preds, batchsize, inputs, targets,
        model, criterion, predict_n_pr, use_n_im, use_2_encoders = False):

    if not use_2_encoders:
        encoder_hidden = (model.initHiddenEncoder(inputs.size(0)).cuda(),
                    model.initHiddenEncoder(inputs.size(0)).cuda())
    else:
        im_encoder_hidden = (model.initHiddenEncoderIm(inputs.size(0)).cuda(),
                    model.initHiddenEncoderIm(inputs.size(0)).cuda())
        pr_encoder_hidden = (model.initHiddenEncoderPR(inputs.size(0)).cuda(),
                    model.initHiddenEncoderPR(inputs.size(0)).cuda())

    decoder_hidden = (model.initHiddenDecoder(targets.size(0)).cuda(),
                    model.initHiddenDecoder(targets.size(0)).cuda())

    target_length = LEN_SEQ - predict_n_pr - use_n_im

    with th.no_grad():
        loss = 0

        for im in range(use_n_im-1, target_length+use_n_im):

            image_s = [inputs[:,im-i,:,:,:] for i in range(use_n_im - 1, -1, -1)]
            pr_s = [targets[:,im-i,:] for i in range(use_n_im - 1, -1, -1)]

            if not use_2_encoders:
                prediction, encoder_hidden, decoder_hidden = model(image_s, pr_s, use_n_im, predict_n_pr, encoder_hidden, decoder_hidden)
            else:
                prediction, im_encoder_hidden, pr_encoder_hidden, decoder_hidden = model(image_s, pr_s, use_n_im, predict_n_pr, im_encoder_hidden, pr_encoder_hidden, decoder_hidden)

            loss += criterion(prediction, targets[:,im+1:im+predict_n_pr+1,:])/predict_n_pr

            key_tmp = np.linspace(i*target_length*batchsize + (im-use_n_im+1)*batchsize , i*target_length*batchsize + (im-use_n_im+2)*batchsize - 1, batchsize, dtype =int )

            for pred_im in range(predict_n_pr):
                tmp1 = gen_dict_for_json(key_tmp, targets[:,im+pred_im+1,:].cpu())
                tmp2 = gen_dict_for_json(key_tmp, prediction[:,pred_im,:].cpu())

                origins[pred_im] = {**origins[pred_im], **tmp1}
                preds[pred_im] = {**preds[pred_im], **tmp2}

    return loss.item() / target_length, origins, preds


def main(args, num_epochs = 30):

    train_folder = args['train_folder']        # 50
    batchsize = args['batchsize']            # 32
    opt = args['opt']
    learning_rate = args['learning_rate']    # 0.0001
    seed = args['seed']                      # 42
    cuda = args['cuda']                      # True
    load_weight = args['load_weight']        # False,
    load_weight_date = args['load_weight_date']
    model_type = args['model_type']          # "CNN_LSTM_encoder_decoder_images_PR"
    latent_vector = args['latent_vector']
    evaluate_print = 1
    time_gap = args['time_gap']              # 5
    use_sec = args['use_sec']                # 5,
    frame_interval = args['frame_interval']  # 12
    weight_decay = args["weight_decay"]      # 1e-3
    use_n_episodes = args["use_n_episodes"]    # 320
    test_dir = args["test_dir"]
    # print(args)
    # indicqte randomseed , so that we will be able to reproduce the result in the future
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    # if you are suing GPU
    if cuda:
        th.cuda.manual_seed(seed)
        th.cuda.manual_seed_all(seed)
    th.backends.cudnn.enabled = False
    th.backends.cudnn.benchmark = False
    th.backends.cudnn.deterministic = True
    #---------------------------------------------------------------------------
    print('has cuda?', cuda)


    if load_weight:
        today = load_weight_date
    else:
        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    base_dir = "./Pre/results"+test_dir+"/train_"+ model_type +"_using_" +str(use_sec)+  "_s_to_predict_"+str(time_gap)+ "_s_lr_" + str(learning_rate) + "_" + today
    ress_dir = base_dir+ "/result"
    lable_dir = base_dir+ "/labels"
    weight_dir = base_dir + "/weight"
    img_dir = base_dir + "/img"

    if not load_weight:
        os.mkdir(base_dir)
        os.mkdir(ress_dir)
        os.mkdir(lable_dir)
        os.mkdir(weight_dir)
        os.mkdir(img_dir)

    # parametres general

    im_in_one_second = int(24/frame_interval)
    predict_n_pr = im_in_one_second*time_gap
    use_n_im = im_in_one_second*use_sec
    use_LSTM = False
    use_stack = False
    use_n_channels = 3
    seq_per_ep = SEQ_PER_EPISODE_C
    use_2_encoders = False
    # parametr for different models
    if 'LSTM' in model_type:
        use_LSTM = True
    else:
        seq_per_ep = int(360/use_n_im)

    if 'stack' in model_type:
        use_stack = True
        use_n_channels = 3*use_n_im

    early_stopping = EarlyStopping(verbose=True)
    # parametr for different models

    # Will be changed to separe plus efective
    train_labels, val_labels, test_labels = loadLabels(train_folder, 0, use_n_episodes, seq_per_ep, p_train=0.7, p_val=0.15, p_test=0.15)

    # Keywords for pytorch dataloader, augment num_workers could work faster
    kwargs = {'num_workers': 4, 'pin_memory': False} if cuda else {}
    # Create data loaders

    train_loader = th.utils.data.DataLoader(
                                                JsonDataset(train_labels,
                                                            preprocess=True,
                                                            folder_prefix=train_folder,
                                                            predict_n_im = predict_n_pr,
                                                            use_n_im = use_n_im,
                                                            seq_per_ep = seq_per_ep,
                                                            use_LSTM = use_LSTM,
                                                            use_stack = use_stack),
                                                batch_size=batchsize,
                                                shuffle=True,
                                                **kwargs
                                            )

    val_loader = th.utils.data.DataLoader(
                                            JsonDataset(val_labels,
                                                        preprocess=True,
                                                        folder_prefix=train_folder,
                                                        predict_n_im = predict_n_pr,
                                                        use_n_im = use_n_im,
                                                        seq_per_ep = seq_per_ep,
                                                        use_LSTM = use_LSTM,
                                                        use_stack = use_stack),
                                            batch_size=batchsize,
                                            shuffle=True,
                                            **kwargs
                                        )

    test_loader = th.utils.data.DataLoader(
                                            JsonDataset(test_labels,
                                                        preprocess=True,
                                                        folder_prefix=train_folder,
                                                        predict_n_im = predict_n_pr,
                                                        use_n_im = use_n_im,
                                                        seq_per_ep = seq_per_ep,
                                                        use_LSTM = use_LSTM,
                                                        use_stack = use_stack),
                                            batch_size=batchsize,
                                            shuffle=True,
                                            **kwargs
                                        )


    n_train, n_val, n_test = len(train_loader)*batchsize, len(val_loader)*batchsize, len(test_loader)*batchsize

    print("modeltype----", model_type)
    if model_type == "CNN_stack_PR_FC":
        model = CNN_stack_PR_FC(num_channel=use_n_channels, cnn_fc_size = 1024 + use_n_im*2, num_output=predict_n_pr*2 )
    elif model_type == "CNN_PR_FC":
        model = CNN_PR_FC(cnn_fc_size = use_n_im*1026, num_output=predict_n_pr*2)
    elif model_type == "CNN_stack_FC_first":
        model = CNN_stack_FC_first(num_channel = use_n_channels,  cnn_fc_size = 1024, num_output=predict_n_pr*2)
    elif model_type == "CNN_stack_FC":
        model = CNN_stack_FC(num_channel = use_n_channels,  cnn_fc_size = 1024, num_output=predict_n_pr*2)
    elif model_type == "CNN_LSTM_encoder_decoder_images_PR":
        model = CNN_LSTM_encoder_decoder_images_PR(encoder_input_size = use_n_im*1026, encoder_hidden_size = latent_vector, decoder_hidden_size = latent_vector,  output_size = 2*predict_n_pr)
        #pretrained model
        use_pretrainted(model, AutoEncoder())
    elif model_type == "LSTM_encoder_decoder_PR":
        model = LSTM_encoder_decoder_PR(encoder_input_size = use_n_im*2, encoder_hidden_size = 300, decoder_hidden_size = 300,  output_size = 2*predict_n_pr)
    elif model_type == "CNN_LSTM_encoder_decoder_images":
        model = CNN_LSTM_encoder_decoder_images(encoder_input_size = use_n_im*1024, encoder_hidden_size = latent_vector, decoder_hidden_size = latent_vector,  output_size = 2*predict_n_pr)
        #pretrained model
        use_pretrainted(model, AutoEncoder())
    elif model_type == 'CNN_LSTM_decoder_images_PR':
        model = CNN_LSTM_decoder_images_PR(decoder_input_size = use_n_im*1026, decoder_hidden_size = 1000, output_size = 2*predict_n_pr)
        #pretrained model
        CNN_part_tmp = AutoEncoder()
        use_pretrainted(model, AutoEncoder())
    elif model_type == "CNN_LSTM_image_encoder_PR_encoder_decoder":
        model = CNN_LSTM_image_encoder_PR_encoder_decoder(im_encoder_input_size = use_n_im*1024, pr_encoder_input_size = use_n_im*2 , im_encoder_hidden_size = 600, pr_encoder_hidden_size = 300, decoder_hidden_size = 900,  output_size = predict_n_pr*2)
        #pretrained model
        use_pretrainted(model, AutoEncoder())
        use_2_encoders = True
    else:
        raise ValueError("Model type not supported")


    if load_weight:
        model.load_state_dict(torch.load(weight_dir+"/" + model_type + "_predict_" + str(time_gap) + "_s_using_" + str(use_sec) + "_s_lr_" + str(learning_rate) + "_tmp.pth"))

    if cuda:
        model.cuda()

    # Optimizers
    if opt == "adam":
        optimizer = th.optim.Adam(model.parameters(),
                                    lr=learning_rate,
                                    weight_decay=weight_decay,
                                    amsgrad = True
                                )
    elif opt == "sgd":
        optimizer = th.optim.SGD(model.parameters(),
                            lr=learning_rate,
                            momentum=0.9,
                            weight_decay=weight_decay,
                            nesterov=True)

    # Loss functions
    loss_fn = nn.MSELoss(reduction = 'sum')

    best_val_error = np.inf
    best_train_loss = np.inf

    # error list for updata loss figure
    train_err_list = []
    val_err_list = []
    # epoch list
    xdata = []


    model_weight = "/" + model_type + "_predict_" + str(time_gap) + "_s_using_" + str(use_sec) + "_s_lr_" + str(learning_rate) + "_tmp.pth"
    best_model_weight_path = weight_dir + model_weight
    tmp_str = '/' + model_type + "_predict_" + str(time_gap) + "_s_using_" + str(use_sec) + "_s_lr_" + str(learning_rate)

    plt.figure(1)
    fig = plt.figure(figsize=(22,15))
    ax = fig.add_subplot(111)
    li, = ax.plot(xdata, train_err_list, 'b-', label='train loss')
    l2, = ax.plot(xdata, val_err_list, 'r-', label='val loss')
    plt.legend(loc='upper right', fontsize=18)
    fig.canvas.draw()
    plt.title("Evolution of loss function")
    plt.xlabel("Epochs", fontsize = 18)
    plt.ylabel("Loss function", fontsize = 18)
    plt.show(block=False)



    # Finally, launch the training loop.
    start_time = time.time()


    print("Starting training...")
    # We iterate over epochs:

    for epoch in tqdm(range(num_epochs)):
        # Switch to training mode
        model.train()
        train_loss, val_loss = 0.0, 0.0

        for k, data in enumerate(train_loader):
            # if k == 0:
                # print("CNN_p.state_dict() ",  model.state_dict())
            if use_LSTM:
                inputs, p_and_roll = data[0], data[1]
                if cuda:
                    inputs, p_and_roll = inputs.cuda(), p_and_roll.cuda()
                # Convert to pytorch variables
                inputs, p_and_roll  = Variable(inputs), Variable(p_and_roll)

                loss = train(inputs, p_and_roll, model, optimizer, loss_fn, predict_n_pr, use_n_im, use_2_encoders)
                train_loss += loss

            else:
                inputs, p_and_roll, targets = data[0], data[1], data[2]
                if cuda:
                    inputs, p_and_roll, targets = inputs.cuda(), p_and_roll.cuda(), targets.cuda()
                # Convert to pytorch variables
                inputs, p_and_roll, targets = Variable(inputs), Variable(p_and_roll),Variable(targets)

                optimizer.zero_grad()
                predictions = model(inputs, p_and_roll, use_n_im, cuda)
                loss = loss_fn(predictions, targets)/ predict_n_pr

                loss.backward()
                train_loss += loss.item()
                optimizer.step()


        train_error = (train_loss / n_train)*100

        # Do a full pass on validation data
        with th.no_grad():
            model.eval()
            for data in val_loader:
                if use_LSTM:
                    inputs, p_and_roll = data[0], data[1]
                    if cuda:
                        inputs, p_and_roll = inputs.cuda(), p_and_roll.cuda()
                    # Convert to pytorch variables
                    inputs, p_and_roll = Variable(inputs), Variable(p_and_roll)

                    loss = eval(inputs, p_and_roll, model, loss_fn, predict_n_pr, use_n_im, use_2_encoders)
                    val_loss += loss

                else:
                    inputs, p_and_roll, targets = data[0], data[1], data[2]
                    if cuda:
                        inputs, p_and_roll, targets = inputs.cuda(), p_and_roll.cuda(), targets.cuda()
                    # Convert to pytorch variables
                    inputs, p_and_roll, targets = Variable(inputs), Variable(p_and_roll),Variable(targets)


                    predictions = model(inputs, p_and_roll, use_n_im, cuda)
                    loss = loss_fn(predictions, targets)/ predict_n_pr

                    val_loss += loss.item()


            # Compute error per sample
            val_error = (val_loss / n_val)*100
            early_stopping(val_error, model, best_model_weight_path, cuda)

            # if val_error < best_val_error:
            #     best_val_error = val_error
            #     # Move back weights to cpu
            #     if cuda:
            #         model.cpu()
            #     # Save Weights
            #     th.save(model.state_dict(), best_model_weight_path)
            #
            #     if cuda:
            #         model.cuda()
            if train_error < best_train_loss:
                best_train_loss = train_error

        if (epoch + 1) % evaluate_print == 0:
            # update figure value and drawing

            xdata.append(epoch+1)
            train_err_list.append(train_error)
            val_err_list.append(val_error)
            li.set_xdata(xdata)
            li.set_ydata(train_err_list)
            l2.set_xdata(xdata)
            l2.set_ydata(val_err_list)
            ax.relim()
            ax.autoscale_view(True,True,True)
            fig.canvas.draw()

            json.dump(train_err_list, open(ress_dir+tmp_str+"_train_loss.json",'w'))
            json.dump(val_err_list, open(ress_dir+tmp_str+"_val_loss.json",'w'))
            print("  training loss:\t\t{:.6f}".format(train_error))
            print("  validation loss:\t\t{:.6f}".format(val_error))

        if early_stopping.early_stop:
            print("--Early stopping--")
            break


    plt.savefig(img_dir+tmp_str +'_log_losses.png')
    plt.close()



    model.load_state_dict(th.load(best_model_weight_path))

    test_loss = 0.0

    with th.no_grad():

        origins = [{} for i in range(predict_n_pr)]
        origin_names = [lable_dir+ '/origin' + model_type +'_use_' + str(use_sec) + '_s_to_predict_'+str(i+1)+':'+str(predict_n_pr)+'_lr_'+str(learning_rate)+'.json' for i in range(predict_n_pr)]
        preds = [{} for i in range(predict_n_pr)]
        pred_names = [lable_dir+'/pred' + model_type +'_use_' + str(use_sec) + '_s_to_predict_'+str(i+1)+':'+str(predict_n_pr)+'_lr_'+str(learning_rate)+'.json' for i in range(predict_n_pr)]

        for key, data  in enumerate(test_loader):
            if use_LSTM:
                inputs, p_and_roll = data[0], data[1]
                if cuda:
                    inputs, p_and_roll = inputs.cuda(), p_and_roll.cuda()
                # Convert to pytorch variables
                inputs, p_and_roll = Variable(inputs), Variable(p_and_roll)

                loss, origins, preds  = test(key, origins, preds , batchsize, inputs, p_and_roll, model, loss_fn, predict_n_pr, use_n_im, use_2_encoders)
                test_loss += loss

            else:
                inputs, p_and_roll, targets = data[0], data[1], data[2]
                if cuda:
                    inputs, p_and_roll, targets = inputs.cuda(), p_and_roll.cuda(), targets.cuda()
                # Convert to pytorch variables
                inputs, p_and_roll, targets = Variable(inputs), Variable(p_and_roll),Variable(targets)


                predictions = model(inputs, p_and_roll, use_n_im, cuda)

                key_tmp = np.linspace(key*batchsize , (key+1)*batchsize, batchsize, dtype =int )
                for pred_im in range(predict_n_pr):
                    tmp1 = gen_dict_for_json(key_tmp, targets[:,pred_im,:].cpu())
                    tmp2 = gen_dict_for_json(key_tmp, predictions[:,pred_im,:].cpu())

                    origins[pred_im] = {**origins[pred_im], **tmp1}
                    preds[pred_im] = {**preds[pred_im], **tmp2}

                loss = loss_fn(predictions, targets)/ predict_n_pr

                test_loss += loss.item()





        for i in range(predict_n_pr):
            json.dump(preds[i], open(pred_names[i],'w'))
            json.dump(origins[i], open(origin_names[i],'w'))

    final_test_loss = (test_loss /n_test)*100

    print("Final results:")
    print("  best avg validation loss [normalized (-1 : 1) ]:\t\t{:.6f}".format(min(val_err_list)))
    print("  test avg loss[normalized (-1 : 1) ]:\t\t\t{:.6f}".format(final_test_loss))

    # write result into result.txt

    final_time = (time.time() - start_time)/60
    print("Total train time: {:.2f} mins".format(final_time))
    tmp2 = use_n_im
    if use_LSTM:
        tmp2 = LEN_SEQ


    write_result(args, [model], [optimizer], result_file_name = ress_dir + "/result.txt",
                best_train_loss = best_train_loss, best_val_loss = early_stopping.val_loss_min,
                final_test_loss = final_test_loss, time = final_time, seq_per_ep = seq_per_ep,
                seq_len = tmp2, num_epochs = num_epochs
                )


    return {"best_train_loss": best_train_loss, "best_val_loss": early_stopping.val_loss_min, "final_test_loss": final_test_loss}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train a line detector')
    parser.add_argument('-tf', '--train_folder', help='Training folder', type=str, required=True)
    parser.add_argument('--num_epochs', help='Number of epoch', default= 50, type=int)
    parser.add_argument('--batchsize', help='Batch size', default= 32, type=int)
    parser.add_argument('-lr', '--learning_rate', help='Learning rate', default=1e-4, type=float)
    parser.add_argument('--opt', help='Choose optimizer: cnn', default="adam", type=str, choices=['adam', 'sgd'])
    parser.add_argument('--test_dir', help='test_dir', default="", type=str)


    parser.add_argument('--seed', help='Random Seed', default=42, type=int)
    parser.add_argument('--no_cuda', action='store_true', default=False, help='Disables CUDA training')

    parser.add_argument('--load_model', action='store_true', default=False, help='LOAD_MODEL (to continue training)')
    parser.add_argument('--load_weight_date', help='Enter test date', default="2019-07-05 00:36", type=str)

    parser.add_argument('--model_type', help='Model type: cnn', default="CNN_LSTM_encoder_decoder_images_PR", type=str, choices=['CNN_stack_FC_first', 'CNN_stack_FC', 'CNN_LSTM_image_encoder_PR_encoder_decoder', 'CNN_PR_FC', 'CNN_LSTM_encoder_decoder_images', 'LSTM_encoder_decoder_PR', 'CNN_stack_PR_FC', 'CNN_LSTM_encoder_decoder_images_PR', 'CNN_LSTM_decoder_images_PR'])
    parser.add_argument('--latent_vector', help='Size of latent vector for LSTM', default= 300, type=int)

    parser.add_argument('-t', '--time_gap', help='Time gap', default= 10, type=int)
    parser.add_argument('-u', '--use_sec', help='How many seconds using for prediction ', default= 10, type=int)
    parser.add_argument('--frame_interval', help='frame_interval which used for data generetion ', default= 12, type=int)
    parser.add_argument('-wd', '--weight_decay', help='Weight_decay', default=1e-3, type=float)
    parser.add_argument('--use_n_episodes', help='How many episodes use as dataset ', default= 540, type=int)

    parser.add_argument('--test', help='Test hyperparameters', default=0, type=int)
    args = parser.parse_args()

    args.cuda = (not args.no_cuda) and th.cuda.is_available()

    if args.test == 0:
        hyperparams = {}
        hyperparams['train_folder'] = args.train_folder
        hyperparams['batchsize'] = args.batchsize
        hyperparams['learning_rate'] = args.learning_rate
        hyperparams['opt'] = args.opt
        hyperparams['seed'] = args.seed
        hyperparams['cuda'] = args.cuda
        hyperparams['load_weight'] = args.load_model
        hyperparams['load_weight_date'] = args.load_weight_date
        hyperparams['model_type'] = args.model_type
        hyperparams['latent_vector'] = args.latent_vector
        hyperparams['time_gap'] = args.time_gap
        hyperparams['use_sec'] = args.use_sec
        hyperparams['frame_interval'] = args.frame_interval
        hyperparams["weight_decay"] = args.weight_decay
        hyperparams["use_n_episodes"] = args.use_n_episodes
        hyperparams['test_dir'] = args.test_dir

        while(True):
            try:
                main(hyperparams, args.num_epochs)
                break
            except RuntimeError:
                hyperparams['batchsize'] = int(hyperparams['batchsize']/2)
                continue
    elif args.test == 1:

        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_dir = "/HB_train_"+args.model_type+"_"+str(today)
        args.test_dir = test_dir
        base_dir = "./Pre/results" + test_dir
        os.mkdir(base_dir)
        hb = Hyperband(args, get_params, main)
        results, best_results = hb.run(skip_last = 1, dry_run = False, hb_result_file = base_dir+"/hb_result.json", hb_best_result_file = base_dir+"/hb_best_result.json" )
        json.dump(results, open(base_dir+"/hb_result.json",'w'))
        json.dump(best_results, open(base_dir+"/hb_best_result.json",'w'))
        print('\n\n-------------------------FINISH------------------------')
        # print(results)
    elif args.test == 2:
        # print("to complete!")
        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_dir = "/MT_train_"+args.model_type+"_"+str(today)
        base_dir = "./Pre/results" + test_dir
        os.mkdir(base_dir)
        xdata = []
        parm0_lr = []
        parm1_time_gap = []
        parm2_use_n_seconds_to_predict = []
        parm3_best_train_loss = []
        parm4_best_val_loss = []
        parm5_best_test_loss = []
        time_gap_p = [5]
        lr_p = [1e-4, 3e-4, 9e-4, 1e-3, 3e-3]
        use_n_seconds_to_predict = [5]



        for lr in lr_p:
            to_plot = []
            plt.figure(lr*1000000)
            # resize pic to show details

            for ii in use_n_seconds_to_predict:
                for tg in time_gap_p:
                    hyperparams = {}
                    hyperparams['train_folder'] = args.train_folder
                    hyperparams['batchsize'] = args.batchsize
                    hyperparams['learning_rate'] = 1e-3
                    hyperparams['opt'] = args.opt
                    hyperparams['seed'] = args.seed
                    hyperparams['cuda'] = args.cuda
                    hyperparams['load_weight'] = args.load_model
                    hyperparams['load_weight_date'] = args.load_weight_date
                    hyperparams['model_type'] = args.model_type
                    hyperparams['latent_vector'] = args.latent_vector
                    hyperparams['time_gap'] = tg
                    hyperparams['use_sec'] = ii
                    hyperparams['frame_interval'] = args.frame_interval
                    hyperparams['weight_decay'] = lr
                    hyperparams['use_n_episodes'] = args.use_n_episodes
                    hyperparams['test_dir'] = args.test_dir

                    res_dict = main(hyperparams, args.num_epochs)
                    parm0_lr.append(lr)
                    parm1_time_gap.append(tg)
                    parm2_use_n_seconds_to_predict.append(ii)
                    parm3_best_train_loss.append(res_dict['best_train_loss'])
                    parm4_best_val_loss.append(res_dict['best_val_loss'])
                    parm5_best_test_loss.append(res_dict['final_test_loss'])

                to_plot.append(parm3_best_train_loss)




                for x in range(len(parm3_best_train_loss)):
                    print("---------------------------------------")
                    print("lr       - > ", parm0_lr[x])
                    print("time_gap - > ", parm1_time_gap[x])
                    print("number_im -> ", parm2_use_n_seconds_to_predict[x])
                    print("train     ->", parm3_best_train_loss[x])
                    print("val       ->", parm4_best_val_loss[x])
                    print("test      ->", parm5_best_test_loss[x])

                parm0_lr = []
                parm1_time_gap = []
                parm2_use_n_seconds_to_predict = []
                parm3_best_train_loss = []
                parm4_best_val_loss = []
                parm5_best_test_loss = []

            for ii in range(len(use_n_seconds_to_predict)):
                plt.plot(time_gap_p, to_plot[ii] , linewidth=1, alpha=0.9, label="test error using: " + str(use_n_seconds_to_predict[ii]) + "sec")

            plt.title("test_error - time_gap")
            plt.xlabel("Time_gap")
            plt.ylabel("Test_error")
            plt.legend(loc='upper right')
            plt.savefig(base_dir+'/error_test_lr_'+str(lr)+'.png')
            plt.close()
