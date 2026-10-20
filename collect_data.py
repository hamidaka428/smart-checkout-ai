import cv2
import os
from picamera2 import Picamera2

# Име на продукта (СМЕНЯЙ ГО ЗА ВСЕКИ НОВ ПРОДУКТ!)
PRODUCT_NAME = "DESK_KBARD"

# Създаване на папка за продукта
save_dir = f"dataset/{PRODUCT_NAME}"
os.makedirs(save_dir, exist_ok=True)

print(f"--- Dataset Collector ---")
print(f"Saving images for: {PRODUCT_NAME}")
print("Press 's' to save a picture. Press 'q' to quit.")

picam2 = Picamera2()
config = picam2.create_preview_configuration(main={"size": (640, 480)})
picam2.configure(config)
picam2.start()

img_count = 0

try:
    while True:
        frame = picam2.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Същият правоъгълник като в главната програма
        height, width, _ = frame.shape
        top_left = (int(width/2 - 225), int(height/2 - 175))
        bottom_right = (int(width/2 + 225), int(height/2 + 175))
        
        # Рисуваме квадрата за ориентация
        display_frame = frame.copy()
        cv2.rectangle(display_frame, top_left, bottom_right, (255, 0, 0), 2)
        cv2.putText(display_frame, f"Saved: {img_count}/30 (Press 's')", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        cv2.imshow("Dataset Collector", display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Изрязваме и запазваме!
            roi_frame = frame[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
            img_path = os.path.join(save_dir, f"{PRODUCT_NAME}_{img_count}.jpg")
            cv2.imwrite(img_path, roi_frame)
            print(f"Saved: {img_path}")
            img_count += 1

finally:
    picam2.stop()
    cv2.destroyAllWindows()
