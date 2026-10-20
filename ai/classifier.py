import os
import cv2
import numpy as np
import time
import tensorflow as tf


class ObjectClassifier:
    """
    AI Object Classification Module powered by TensorFlow Lite.
    Compatible with the Smart Checkout 15-class model.
    """

    def __init__(
        self,
        model_path="ai/model/model_unquant.tflite",
        label_path="ai/model/labels.txt"
    ):
        print("[AI Module] Waking up the Neural Network...")

        self.captures_dir = "captures"

        if not os.path.exists(self.captures_dir):
            os.makedirs(self.captures_dir)

        # Зареждане на TFLite модела
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Проверка на входа
        input_shape = self.input_details[0]["shape"]
        input_dtype = self.input_details[0]["dtype"]

        print(f"[AI Module] Input shape: {input_shape}")
        print(f"[AI Module] Input dtype: {input_dtype}")

        # Нашият модел очаква [1, 224, 224, 3] float32
        if tuple(input_shape) != (1, 224, 224, 3):
            raise ValueError(
                f"Unexpected model input shape: {input_shape}"
            )

        if input_dtype != np.float32:
            raise ValueError(
                f"Unexpected model input dtype: {input_dtype}"
            )

        # Зареждане на имената на продуктите
        self.labels = []

        with open(label_path, "r", encoding="utf-8") as f:
            for line in f:
                clean_label = line.strip()

                if clean_label:
                    self.labels.append(clean_label)

        if len(self.labels) != 15:
            raise ValueError(
                f"Expected 15 labels, but found {len(self.labels)}"
            )

        print(
            f"[AI Module] Brain loaded successfully! "
            f"I know {len(self.labels)} items."
        )

        for index, label in enumerate(self.labels):
            print(f"[AI Module] {index}: {label}")

    def predict_from_frame(self, frame):
        """
        Prepares the image, feeds it to the AI,
        and returns the highest prediction.
        """

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        image_path = os.path.join(
            self.captures_dir,
            f"ai_scan_{timestamp}.jpg"
        )

        if frame is not None:
            cv2.imwrite(image_path, frame)

        if frame is None:
            raise ValueError("Received an empty camera frame.")

        # Resize to the model input size
        img = cv2.resize(frame, (224, 224))

        # Convert to float32.
        # IMPORTANT:
        # The TFLite model itself contains Rescaling:
        # 0..255 -> -1..+1
        #
        # Therefore we DO NOT normalize here.
        img_array = np.asarray(img, dtype=np.float32)

        # Add batch dimension
        input_data = np.expand_dims(img_array, axis=0)

        # Run inference
        self.interpreter.set_tensor(
            self.input_details[0]["index"],
            input_data
        )

        self.interpreter.invoke()

        output_data = self.interpreter.get_tensor(
            self.output_details[0]["index"]
        )

        predictions = np.squeeze(output_data)

        # Find the class with the highest confidence
        highest_confidence_index = int(np.argmax(predictions))

        predicted_product = self.labels[highest_confidence_index]

        confidence = float(
            predictions[highest_confidence_index]
        )

        return predicted_product, confidence
