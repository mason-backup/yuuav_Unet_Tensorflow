# ===================================================================================== #
# coding:utf-8
"""module, service for network as a batch input. creating a queue-based input pipeline.
define the core method batch_input, and also can do module testing

2018/12/04
tensorflow ==1.11
python ==2.7.15

Note:
    at module testing, we using user request stop to stop the coord-threads.
    coord.join(threads): hang on, and waiting to stop,
                        (the threads will stop after the coord-threads stop)
    tf.local_variables_initializer() is needed, and must before the cooord= and threads=
"""
# ===================================================================================== #


import tensorflow as tf
import numpy as np
from config import image_size, BS, queue_capacity, epochs, num_queue_threads, iter_each_epoch, num_classes


def batch_input(record_file, batch_size=BS, class_num=num_classes):
    """core method for input pipeline
    Note:
        capacity:An integer. The maximum number of elements in the queue.
        min_after_dequeue: Minimum number elements in the queue after a
        dequeue, used to ensure a level of mixing of elements, and
        batch_size + min_after_dequeue = capacity.

        the "num_epochs" of string_input_producer is the limited epochs, means the label of epoch, not the count.
        using for queue control, when achieve the limited then report a tf.errors.OutOfRangeError.
        eg: epochs=10. then who to set num_epochs?  it must be >=  epochs,
        otherwise it will stop before your max_iters. set to None should be fine.

    :param
        record_filelist: A string list, consist of the tfrecords filename list.
        batch_size: a inter, define how many images  pass to the network each time.
        and I think the batch_size for the evaluate(val/test) should be much bigger than train
    :return:
        A batch, (a tensor ) with shape (batch_size, image_size, image_size, channel), for rgb, the channel=3
    """
    feature_dict = {
        'name': tf.FixedLenFeature([], tf.string),
        'image': tf.FixedLenFeature([], tf.string),
        'mask': tf.FixedLenFeature([], tf.string)}

    with tf.name_scope("input"):
        filename_queue = tf.train.string_input_producer([record_file], num_epochs=epochs)

        reader = tf.TFRecordReader()
        _, serialized_example = reader.read(filename_queue)

        features = tf.parse_single_example(serialized_example, features=feature_dict)

    nm = features['name']

    with tf.name_scope("decode_process"):
        img = tf.decode_raw(features['image'], tf.uint8)
        img = tf.reshape(img, [image_size, image_size, 3])

        img = (tf.cast(img, tf.float32) - [104.0, 117.0, 123.0]) * (1. / 255)   # ?
        # img = (tf.cast(img, tf.float32))

        # img = tf.cast(img, tf.float32) * (1. / 255) - 0.5

        mask = tf.decode_raw(features['mask'], tf.uint8)
        mask = tf.reshape(mask, [image_size, image_size, class_num])    # the mask/lable, is not rgb image. is label ID

        # mask = (tf.cast(mask, tf.float32) - [104.0, 117.0, 123.0]) * (1. / 255)
        # mask = tf.cast(mask, tf.float32) * (1. / 255) - 0.5

    name_batch, img_batch, label_batch = tf.train.shuffle_batch([nm, img, mask],
                                                                batch_size=batch_size,
                                                                capacity=queue_capacity,
                                                                min_after_dequeue=0, num_threads=num_queue_threads)
    return name_batch, img_batch, label_batch


if __name__ == '__main__':
    print '***************** module testing ******************'
    image_size = 256

    with tf.Session() as sess:
        names, images, labels = batch_input("./data_voc/train.tfrecords", 8)

        sess.run(tf.local_variables_initializer())
        sess.run(tf.global_variables_initializer())

        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(coord=coord)
        try:
            while not coord.should_stop():
                for i in range(1, epochs+1):
                    for j in range(1, iter_each_epoch+1):
                        names_, images_, labels_ = sess.run([names, images, labels])
                        print '\n{0}/{1}epohos; {2}/{3}:\n'.format(i, epochs, j, iter_each_epoch), 'filename_in_batch:',\
                            names_, "\noutput_src_batch_shape:", images_.shape,\
                            '\noutput_label_batch_shape:', labels_.shape

                print "\nfinished,\nachieve the user's iter_max, request coord stop ! "
                coord.request_stop()
        except tf.errors.OutOfRangeError:
            print 'done! limit epochs achieved.'
        finally:
            coord.request_stop()
            coord.join(threads)

