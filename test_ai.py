from picamera2 import Picamera2
from ai.classifier import ObjectClassifier
import time


print("[TEST] Starting camera...")

camera = Picamera2()

camera.configure(
    camera.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
)

camera.start()

print("[TEST] Waiting for camera...")
time.sleep(2)

print("[TEST] Capturing image...")

frame = camera.capture_array()

camera.stop()

print("[TEST] Loading AI model...")

classifier = ObjectClassifier()

print("[TEST] Running prediction...")

product, confidence = classifier.predict_from_frame(frame)

print()
print("========== AI TEST RESULT ==========")
print(f"Product:    {product}")
print(f"Confidence: {confidence:.2%}")
print("====================================")
