# coding=utf-8
# Copyright 2021 The TensorFlow Datasets Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Wikipedia-based Image Text (WIT) Dataset for the Kaggle competition."""
import base64
import csv
import gzip
import io
import sys

import tensorflow as tf
import tensorflow_datasets.public_api as tfds

csv.field_size_limit(sys.maxsize)

_DESCRIPTION = """
Wikipedia - Image/Caption Matching Kaggle Competion.

This competition is organized by the
[Research team](https://research.wikimedia.org/) at the
[Wikimedia Foundation](https://wikimediafoundation.org/).
This competition is based on the
[WIT dataset](https://github.com/google-research-datasets/wit) published by
Google Research as detailed in this\
[SIGIR paper](https://dl.acm.org/doi/abs/10.1145/3404835.3463257).

In this competition, you’ll build a model that automatically retrieves the text
closest to an image. Specifically, you'll train your model to associate given
images with article titles or complex captions, in multiple languages.
The best models will account for the semantic granularity of Wikipedia images.
If successful, you'll be contributing to the accessibility of the largest
online encyclopedia. The millions of Wikipedia readers and editors will be able
to more easily understand, search, and describe media at scale. As a result,
you’ll contribute to an open model to improve learning for all.
"""

_CITATION = """
@article{srinivasan2021wit,
  title={WIT: Wikipedia-based Image Text Dataset for Multimodal Multilingual Machine Learning},
  author={Srinivasan, Krishna and Raman, Karthik and Chen, Jiecao and Bendersky, Michael and Najork, Marc},
  journal={arXiv preprint arXiv:2103.01913},
  year={2021}
}
"""


class WitKaggleConfig(tfds.core.BuilderConfig):
  """BuilderConfig for WitKaggle."""

  def __init__(self,
               *,
               split_specific_features=None,
               resnet_embedding_shape=2048,
               **kwargs):
    """BuilderConfig for WitKaggle.

    Args:
      split_specific_features: tfds.features.FeaturesDict. The features for the
        specific WitKaggle split.
      resnet_embedding_shape: shape of resnet embeddings.
      **kwargs: keyword arguments forwarded to super.
    """
    super(WitKaggleConfig, self).__init__(**kwargs)

    # Features common to both train and test splits.
    common_features = tfds.features.FeaturesDict({
        "caption_title_and_reference_description":
            tfds.features.Text(
            ),  # Caption for the image_url (if existent, else '').
        "image_url":
            tfds.features.Text(),
        "image":
            tfds.features.Image(
            ),  # Base64 encoded image bytes (if existent, else a blank image).
        "metadata_url":
            tfds.features.Text(
            ),  # Url to the image's commons page (if existent, else '').
        "embedding":
            tfds.features.Tensor(
                shape=(resnet_embedding_shape,), dtype=tf.float32
            ),  # A tensor of 2048 floats (if existent, else zeros).
    })
    self.features = tfds.features.FeaturesDict({
        **common_features,
        **split_specific_features
    })
    self.split_specific_features = split_specific_features
    self.resnet_embedding_shape = resnet_embedding_shape
    # For missing images, we use base64 encoded bytes of a blank image as
    # pixels, and a zeroed vector of dimensionality (2048,) as resnit embedding.
    self.EMPTY_IMAGE_BYTES = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HgAGgwJ/lK3Q6wAAAABJRU5ErkJggg=="
    self.EMPTY_RESNET_EMBEDDING = [0] * resnet_embedding_shape


class WitKaggle(tfds.core.GeneratorBasedBuilder):
  """DatasetBuilder for wit_kaggle dataset."""

  VERSION = tfds.core.Version("1.0.0")
  RELEASE_NOTES = {
      "1.0.0":
          """Initial release. It provides the train and test splits from the
      Wikipedia - Image/Caption Matching Kaggle competition
      (https://www.kaggle.com/c/wikipedia-image-caption/).

      The goal of the competition is to build a model that automatically
      retrieves the text closest to an image. Specifically, the model shuld be
      trained to associate given images with article titles or complex captions,
      in multiple languages. The best models will account for the semantic
      granularity of Wikipedia images.

      Note that this release doesn't provide the ground truth for the test set,
      as it hasn't been provided by the Kaggle competition yet.
      """,
  }

  # pytype: disable=wrong-keyword-args
  # In the Wikipedia - Image/Caption Matching competition, train samples are
  # associated with a rich set of metadata, while test samples only have a
  # sample_id and four image-related fields.
  BUILDER_CONFIGS = [
      WitKaggleConfig(
          name="train",
          description="Training set for the Wikipedia-Image/Caption Matching competition.",
          split_specific_features=tfds.features.FeaturesDict({
              "language": tfds.features.Text(),
              "page_url": tfds.features.Text(),
              "image_url": tfds.features.Text(),
              "page_title": tfds.features.Text(),
              "section_title": tfds.features.Text(),
              "hierarchical_section_title": tfds.features.Text(),
              "caption_reference_description": tfds.features.Text(),
              "caption_attribution_description": tfds.features.Text(),
              "caption_alt_text_description": tfds.features.Text(),
              "mime_type": tfds.features.Text(),
              "original_height": tf.int32,
              "original_width": tf.int32,
              "is_main_image": tf.bool,
              "attribution_passes_lang_id": tf.bool,
              "page_changed_recently": tf.bool,
              "context_page_description": tfds.features.Text(),
              "context_section_description": tfds.features.Text(),
              "caption_title_and_reference_description": tfds.features.Text(),
          })),
      WitKaggleConfig(
          name="test",
          description="Test set for the Wikipedia-Image/Caption Matching competition.",
          split_specific_features=tfds.features.FeaturesDict({
              "id": tfds.features.Text(),
              "image_url": tfds.features.Text(),
          })),
  ]
  # pytype: enable=wrong-keyword-args

  MANUAL_DOWNLOAD_INSTRUCTIONS = """
  Depending on the config called, manual_dir should contain some of the
  following subdirectories:
    * train
      - train-{0000x}-of-00005.tsv.zip
      - image_data_train/
        * image_pixels/
          - train_image_pixels_part-00{000-199}.csv.gz
        * resnet_embeddings/
          - train_resnet_embeddings_part-00{000-214}.csv.gz
    * test
      - test.tsv.zip
      - image_data_test/
        * image_pixels/
          - test_image_pixels_part-0000{0-4}.csv
        * resnet_embeddings/
          - test_resnet_embeddings_part-0000{0-9}.csv

  Registration at https://www.kaggle.com/c/wikipedia-image-caption/data
  is needed to get the links to download the dataset.
  """

  def _info(self) -> tfds.core.DatasetInfo:
    """Returns the dataset metadata."""
    return tfds.core.DatasetInfo(
        builder=self,
        description=_DESCRIPTION,
        features=self.builder_config.features,
        supervised_keys=("image_url",
                         "caption_title_and_reference_description"),
        homepage="https://www.kaggle.com/c/wikipedia-image-caption/code",
        citation=_CITATION,
    )

  def _split_generators(self, dl_manager, pipeline):
    """Returns SplitGenerators."""
    if self.builder_config.name == "test":
      archive_path = {
          "samples": [
              tfds.download.Resource(
                  path=dl_manager.manual_dir / "test/test.tsv.zip",
                  extract_method=tfds.download.ExtractMethod.ZIP)
          ],
          "images":
              tfds.download.Resource(path=dl_manager.manual_dir /
                                     "test/image_data_test"),
      }

    else:
      archive_path = {
          "samples": [
              tfds.download.Resource(  # pylint:disable=g-complex-comprehension
                  path=dl_manager.manual_dir /
                  f"train/train-0000{i}-of-00005.tsv.zip",
                  extract_method=tfds.download.ExtractMethod.ZIP)
              for i in range(5)
          ],
          "images":
              tfds.download.Resource(path=dl_manager.manual_dir /
                                     "train/image_data_train"),
      }

    extracted_paths = dl_manager.extract(archive_path)

    return {
        self.builder_config.name:
            self._generate_examples(
                pipeline=pipeline,
                samples_path=extracted_paths["samples"],
                image_pixels_path=extracted_paths["images"] / "image_pixels",
                image_resnet_path=extracted_paths["images"] /
                "resnet_embeddings")
    }

  def _generate_examples(self, pipeline, samples_path, image_pixels_path,
                         image_resnet_path):
    """Processes the dataset and yields examples.

    Args:
      pipeline: the Flume pipeline.
      samples_path: path to the split's sentences.
      image_pixels_path: path to the images' pixel representations.
      image_resnet_path: path to the images' pixel representations.

    Returns:
      Examples.
    """

    def _get_csv_reader(filename):
      if filename.suffix == ".gz":
        g = tf.io.gfile.GFile(filename, "rb")
        f = gzip.open(g, "rt", newline="")
      else:
        f = tf.io.gfile.GFile(filename, "r")
      return csv.reader(f, delimiter="\t")

    def _read_pixel_rows(filename):
      r"""Contains image_url \t image_pixel \t metadata_url."""
      reader = _get_csv_reader(filename)
      for row in reader:
        image_url, image_representation, metadata_url = row
        yield [image_url, (image_representation, metadata_url)]

    def _read_resnet_rows(filename):
      r"""Contains image_url \t resnet_embedding."""
      reader = _get_csv_reader(filename)
      for row in reader:
        image_url, image_representation = row
        yield [image_url, image_representation]

    def _read_samples_rows(folder_path):
      """Contains samples: train and test have different fields."""
      for filename in tf.io.gfile.listdir(folder_path):
        file_path = folder_path / filename
        f = tf.io.gfile.GFile(file_path, "r")
        csv_reader = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_ALL)
        for row in csv_reader:
          sample = {
              feature_key: row[feature_key] for feature_key in
              self.builder_config.split_specific_features.keys()
          }
          yield [row["image_url"], sample]

    def _process_examples(el):
      sample_url, sample_fields = el
      # Each image_url can be associated with multiple samples (e.g., multiple
      # languages).
      for i, sample_info in enumerate(sample_fields["sample_info"]):
        sample_id = f"{i}_{sample_url}"
        sample = {"image_url": sample_url}
        for feature_key in self.builder_config.split_specific_features.keys():
          sample[feature_key] = sample_info[feature_key]
        # Test samples don't have gold captions.
        if "caption_title_and_reference_description" not in sample_info:
          sample["caption_title_and_reference_description"] = ""

        # We output image data only if there is at least one image
        # representation per image_url.
        # Not all of the samples in the competition have corresponding image
        # data. In case multiple different image representations are associated
        # with the same image_url, we don't know which one is correct and don't
        # output any.
        if len(set(sample_fields["image_pixels"])) == 1:
          sample_image, sample_metadata = sample_fields["image_pixels"][0]
          print(io.BytesIO(tf.io.encode_base64(sample_image)))
          sample["image"] = io.BytesIO(base64.b64decode(sample_image))
          sample["metadata_url"] = sample_metadata
        else:
          if len(set(sample_fields["image_pixels"])) > 1:
            beam.metrics.Metrics.counter("image_pixels", "multiple").inc()
          else:
            beam.metrics.Metrics.counter("image_pixels", "missing").inc()
            sample["image"] = io.BytesIO(
                base64.b64decode(self.builder_config.EMPTY_IMAGE_BYTES))
          sample["metadata_url"] = ""

        if len(set(sample_fields["image_resnet"])) == 1:
          image_resnet = [
              float(x) for x in sample_fields["image_resnet"][0].split(",")
          ]
          sample["embedding"] = image_resnet
        else:
          if len(set(sample_fields["image_resnet"])) > 1:
            beam.metrics.Metrics.counter("image_resnet", "multiple").inc()
          else:
            beam.metrics.Metrics.counter("image_resnet", "missing").inc()
          sample["embedding"] = self.builder_config.EMPTY_RESNET_EMBEDDING

        yield sample_id, sample

    beam = tfds.core.lazy_imports.apache_beam

    # Read embeddings and bytes representations from (possibly compressed) csv.
    image_resnet_files = [
        image_resnet_path / f for f in tf.io.gfile.listdir(image_resnet_path)
    ]
    resnet_collection = (
        pipeline
        | "Collection from resnet files" >> beam.Create(image_resnet_files)
        | "Get embeddings per image" >> beam.FlatMap(_read_resnet_rows))

    image_pixel_files = [
        image_pixels_path / f for f in tf.io.gfile.listdir(image_pixels_path)
    ]
    pixel_collection = (
        pipeline
        | "Collection from pixel files" >> beam.Create(image_pixel_files)
        | "Get pixels per image" >> beam.FlatMap(_read_pixel_rows))

    # Read samples from tsv files.
    sample_collection = (
        pipeline
        | "Collection from sample files" >> beam.Create(samples_path)
        | "Get samples" >> beam.FlatMap(_read_samples_rows))

    # Combine the features and yield examples.
    return ({
        "sample_info": sample_collection,
        "image_pixels": pixel_collection,
        "image_resnet": resnet_collection,
    }
            | "Group by image_url" >> beam.CoGroupByKey()
            | "Process and yield examples" >> beam.FlatMap(_process_examples))
