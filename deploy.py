# ===================================================================================== #
# coding: utf-8
"""a individual module from training, deploy the pre-trained model, and show the predict performance.

2018/12/04
tensorflow ==1.11
python ==2.7.15

Note:
    threre mainly contain following parts:
    1. create the network form .mate file
    2. load the parameters
    3. predict
    4. visualization

    there are two way to save and load trained model, here we using frozen model,
    as the checkpoint are to complex and slow for predict.

    !!! the output of network is (BS*h*w, num_class) with the value float 0 to 1 such as 0.01
    !!! a distribution that do not pass through softmax
"""
# ===================================================================================== #


import time
import logging
import argparse

import tensorflow as tf
from visualization import *
import cv2
import numpy as np
from tensorflow.python.platform import gfile


def ckpt_single_image_predictor(img_, meta_, trained_model_path_, h_, w_, class_num_):
    """ restore the variable of model from checkpoint, and predict.
    Note:
        tf.get_collection() will return a list; to get the variable, using tf.get_collection("name")[0]
    :arg
        img_: a rgb image that wait to predict
        meta_: the .meta files from checkpoint, and the graph are stored in .meta file
        trained_model_path_: the checkpoint path
        h_, w_: the image shape of net input, (BS, h_, w_, class_num)
        class_num: length of a single distribute vector

    :return:
        return a visualized rgb image
    """

    img_ = cv2.resize(img_, (h_, w_), interpolation=cv2.INTER_LINEAR)
    img_fd = np.zeros((8, h_, w_, 3), dtype=np.uint8)
    for i in range(8):
        img_fd[i, :, :] = img_
    print img_fd.shape

    with tf.Session() as sess:
        saver = tf.train.import_meta_graph(meta_)
        saver.restore(sess, tf.train.latest_checkpoint(trained_model_path_))

        graph = tf.get_default_graph()

        # op_to_restore = graph.get_tensor_by_name("predict:0")
        op_to_restore = tf.get_collection("predict")[0]

        # print (sess.run(op_to_restore))

        # input = graph.get_tensor_by_name("image_batch:0")
        input_ = tf.get_collection("input")[0]

        # print(sess.run(graph.get_tensor_by_name('conv1_2/weights:0')))

        logging.info("predict ...")

        predict = sess.run(op_to_restore, feed_dict={input_: img_fd})

        predict = predict.reshape((8, h_, w_, class_num_))

        single_ = predict[1, :, :, :]

        single_ = single_.reshape(-1, class_num_)

        logging.info("visualization ...")
        mat_2d = netoutput_2_labelmat(single_, h_, w_, class_num_)

        rgb_image_ = labelmat_2_rgb(mat_2d)

        return rgb_image_


def frozen_predictor(pd_file_path_, single_img, h_, w_, class_num_, BS):
    """ predictor single image, using trained frozen model file.
    Note:
        the input shape of network during triain is (batch_size, h, w, channel),
        while, the single image is (h, w, channel), so using img_mat= np.expand_dims(single_image, axis=0)
        to match the network input.
        you can further do: resize it to meet the net_input shape (batch_size, h, w, channel) by just do copy

        the predict just from frozen file without softmax process;
        so, the raw predict must be following by softmax, for visualization
        or the softmax process be placed at train_main, is ok

    :arg
        img_: a rgb image that wait to predict
        meta_: the .meta files from checkpoint, and the graph are stored in .meta file
        pd_file_path_: : the frozen model file model.pd path
        h_, w_: the image shape of net input, (BS, h_, w_, class_num)
        class_num: length of a single distribute vector

    :return:
        a rgb image with shape (h_, w_, 3)
    """

    single_img = cv2.resize(single_img, (h_, w_), interpolation=cv2.INTER_LINEAR)

    # tmp for single image predict
    img_feed = np.zeros((BS, h_, w_, 3), dtype=np.uint8)
    for i in range(BS):
        img_feed[i, :, :] = single_img

    with tf.Session() as sess:
        with gfile.FastGFile(pd_file_path_ + 'model.pb', 'rb') as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())
            sess.graph.as_default()
            tf.import_graph_def(graph_def, name='')

        sess.run(tf.global_variables_initializer())

        image_tensor = sess.graph.get_tensor_by_name('source_input/image_batch/image_tensor:0')

        logging.info("{}".format(image_tensor))

        op = sess.graph.get_tensor_by_name('predict/predict:0')
        logging.info("{}".format(op))

        logging.info("predict ...")
        predict = sess.run(op, feed_dict={image_tensor: img_feed})
        # predict = sess.run(tf.nn.softmax(predict))

        #  just tmp, for single image predict
        predict = predict.reshape((BS, h_, w_, class_num_))
        predict = predict[0, :, :, :]

        logging.info("predict output shape: {}".format(predict.shape))

        logging.info("visualization ...")
        mat_2d = predict_2_labelmat_new(predict, h_, w_)

        # cv2.imwrite('predict_without_color.png', mat_2d)

        rgb_image_ = labelmat_2_rgb(mat_2d, FLAGS.colormap)

        return rgb_image_


def main(_):

    img = cv2.imread('./predict_image/' + FLAGS.img)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    rgb_image = frozen_predictor(pd_file_path, img, h, w, FLAGS.class_num, FLAGS.batch_size)

    rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    cv2.imwrite('./predict_image/predict.png', rgb_image)


if __name__ == "__main__":

    TM = time.strftime("%Y:%m:%d-%H:%M", time.localtime())
    LOG_FORMAT = "%(asctime)s-%(levelname)s-[line:%(lineno)d] - %(message)s"
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    logging.info("**********************mason_p nn_design(%s)***********************" % TM)

    pd_file_path = "./final_model/"

    h, w = 256, 256

    parser = argparse.ArgumentParser()

    parser.add_argument('--colormap',help="yuuuav, or voc, using for visualization",
                        required=True, default='voc', type=str)
    parser.add_argument('--img', help="image file for predic",
                        required=True, default='test.jpg', type=str)
    parser.add_argument('--class_num', help="the number of class to be classified at training stage",
                        required=True, type=int)

    parser.add_argument('--batch_size', help="the batch_size of frozen model",
                        required=True, type=int)

    FLAGS, _ = parser.parse_known_args()

    tf.app.run()

