import glob
import os

import mxnet as mx
import numpy as np
from PIL import Image
from matplotlib import pyplot as plt
from mxnet import gluon
from scipy import signal


# create dataloader (batch_size, 10, 227, 227)
def create_dataset(path, batch_size, shuffle, augment=False):
    files = sorted(glob.glob(path))
    if augment:
        files = files + files[2:] + files[4:] + files[6:] + files[8:]
    data = np.zeros((int(len(files) / 10), 10, 227, 227))
    i, idx = 0, 0
    for filename in files:
        im = Image.open(filename)
        im = im.resize((227, 227))
        data[idx, i, :, :] = np.array(im, dtype=np.float32) / 255.0
        i = i + 1
        if i > 9:
            i = 0
            idx = idx + 1
    dataset = gluon.data.ArrayDataset(mx.nd.array(data, dtype=np.float32))
    dataloader = gluon.data.DataLoader(dataset, batch_size=batch_size, last_batch="rollover", shuffle=shuffle)

    return dataloader


# perform inference and plot results
def plot_images(path, model, params_file, ctx, output_path):
    dataloader = create_dataset(path, batch_size=1, shuffle=False)

    threshold = 7
    counter = 0
    model.load_parameters(params_file, ctx=ctx)

    try:
        os.mkdir(output_path)
    except:
        pass

    for image in dataloader:
        # perform inference
        image = image.as_in_context(ctx)
        states = model.temporal_encoder.begin_state(batch_size=1, ctx=ctx)
        reconstructed, states = model(image, states)
        # compute difference between reconstructed image and input image
        reconstructed = reconstructed.asnumpy()
        image = image.asnumpy()
        diff = np.abs(reconstructed - image)

        # we need to compute the regularity score per pixel
        image = np.sum(image, axis=1, keepdims=True)
        reconstructed = np.sum(reconstructed, axis=1, keepdims=True)
        diff_max = np.max(diff, axis=1)
        diff_min = np.min(diff, axis=1)
        regularity = diff_max - diff_min
        # perform convolution on regularity matrix
        H = signal.convolve2d(regularity[0, :, :], np.ones((4, 4)), mode='same')

        # if neighboring pixels are anomalous, then mark the current pixel
        x, y = np.where(H > threshold)

        # plt input image, reconstructed image and difference between both
        # fig, (ax0, ax1, ax2,ax3) = plt.subplots(ncols=4, figsize=(10, 5))
        fig, (ax3) = plt.subplots(ncols=1, figsize=(8, 3))
        # ax0.set_axis_off()
        # ax1.set_axis_off()
        # ax2.set_axis_off()

        # ax0.imshow(image[0,0,:,:], cmap=plt.cm.gray, interpolation='nearest')
        # ax0.set_title('input image')
        # ax1.imshow(reconstructed[0,0,:,:], cmap=plt.cm.gray, interpolation='nearest')
        # ax1.set_title('reconstructed image')
        # ax2.imshow(diff[0,0,:,:], cmap=plt.cm.viridis, vmin=0, vmax=1, interpolation='nearest')
        # ax2.set_title('diff ')
        ax3.imshow(image[0, 0, :, :], cmap=plt.cm.gray, interpolation='nearest')
        ax3.scatter(y, x, color='red', s=0.3)
        ax3.set_title('anomalies')
        plt.axis('off')

        # save figure
        counter = counter + 1
        fig.savefig(output_path + "/" + str(counter) + '.png', bbox_inches='tight', pad_inches=0.5)
        plt.close(fig)
