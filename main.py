import time
import json
import urllib.request
import cv2
import os
import threading
import hashlib
import numpy as np

from gpiozero import Buzzer, Button
from RPLCD.i2c import CharLCD

from hardware.sensor import UltrasonicScanner
from ai.classifier import ObjectClassifier
from utils.receipt import ReceiptManager

# Voice
import pygame
from gtts import gTTS

try:
    from picamera2 import Picamera2
except ImportError:
    print("[Error] Picamera2 is missing. Run: sudo apt install python3-picamera2")
    exit(1)


# ============================================================
# DATABASE
# ============================================================

def fetch_product_info(barcode):
    url = f"http://localhost/api.php?barcode={barcode}"

    try:
        response = urllib.request.urlopen(url)
        data = json.loads(response.read().decode('utf-8'))
        return data

    except Exception as e:
        return {"error": str(e)}


# ============================================================
# VOICE ASSISTANT
# ============================================================

def speak_bg(text):
    """
    Generates and plays Bulgarian speech.
    Audio files are cached so repeated messages
    do not need to be generated again.
    """

    try:
        filename = f"audio_{hashlib.md5(text.encode()).hexdigest()}.mp3"

        if not os.path.exists(filename):
            print(f"[Audio] Generating: {text}")
            tts = gTTS(text=text, lang='bg')
            tts.save(filename)

        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()

    except Exception as e:
        print(f"[Audio Error] Cannot play voice: {e}")


# ============================================================
# GLOBAL STATE
# ============================================================

is_processing = False
scanned_cart = []


# ============================================================
# PROCESS PRODUCT
# ============================================================

def process_item_thread(roi_frame, ai_engine, buzzer, lcd):
    global is_processing, scanned_cart

    try:

        # ----------------------------------------------------
        # AI PREDICTION
        # ----------------------------------------------------

        predicted_barcode, confidence = ai_engine.predict_from_frame(
            roi_frame
        )

        print(
            f"\n[AI] Identified barcode: "
            f"{predicted_barcode} "
            f"(Confidence: {confidence * 100:.0f}%)"
        )

        # ----------------------------------------------------
        # IGNORE EMPTY / BACKGROUND
        # ----------------------------------------------------

        if predicted_barcode.upper() in ["EMPTY", "BACKGROUND"]:

            print("[!] Empty background detected. Ignoring.")

            lcd.clear()
            lcd.write_string(
                ' Ready to scan! '.center(16)
            )

            is_processing = False
            return

        # ----------------------------------------------------
        # CONFIDENCE CHECK
        # ----------------------------------------------------

        if confidence < 0.85:

            print(
                "[!] AI is not confident enough. Discarding."
            )

            lcd.clear()
            lcd.write_string(
                ' Not sure... '.center(16)
            )

            lcd.cursor_pos = (1, 0)

            lcd.write_string(
                ' Try again! '.center(16)
            )

            speak_bg(
                "Грешка при сканирането. "
                "Моля, опитайте отново."
            )

            # Double beep
            buzzer.on()
            time.sleep(0.1)
            buzzer.off()

            time.sleep(0.1)

            buzzer.on()
            time.sleep(0.1)
            buzzer.off()

            time.sleep(2)

            lcd.clear()
            lcd.write_string(
                ' Ready to scan! '.center(16)
            )

            is_processing = False
            return

        # ----------------------------------------------------
        # DATABASE LOOKUP
        # ----------------------------------------------------

        product = fetch_product_info(
            predicted_barcode
        )

        # ----------------------------------------------------
        # DATABASE ERROR
        # ----------------------------------------------------

        if "error" in product:

            print(
                f"[API Error] {product['error']}"
            )

            lcd.clear()

            lcd.write_string(
                ' DB Error! '.center(16)
            )

            speak_bg(
                "Продуктът не е намерен "
                "в базата данни."
            )

            time.sleep(2)

        # ----------------------------------------------------
        # PRODUCT FOUND
        # ----------------------------------------------------

        else:

            buzzer.on()
            time.sleep(0.15)
            buzzer.off()

            print(
                f" -> Scanned: "
                f"{product['name']} | "
                f"Price: €{product['price']}"
            )

            # Add product to cart
            scanned_cart.append(product)

            print(
                f"[Cart] Items in cart: "
                f"{len(scanned_cart)}"
            )

            # ------------------------------------------------
            # LCD
            # ------------------------------------------------

            lcd.clear()

            name_text = str(
                product['name']
            )[:16].center(16)

            price_text = (
                f"EUR {product['price']}"
            ).center(16)

            lcd.write_string(name_text)

            lcd.cursor_pos = (1, 0)

            lcd.write_string(price_text)

            # ------------------------------------------------
            # VOICE
            # ------------------------------------------------

            speak_bg(
                "Продуктът е маркиран. "
                "Моля, покажете следващия."
            )

            time.sleep(3)

        print("-" * 50)

        # ----------------------------------------------------
        # READY FOR NEXT PRODUCT
        # ----------------------------------------------------

        lcd.clear()

        lcd.write_string(
            ' Ready to scan! '.center(16)
        )

        print(
            "Ready for next item...\n"
        )

    except Exception as e:

        print(
            f"[Processing Error] {e}"
        )

        lcd.clear()

        lcd.write_string(
            ' System Error '.center(16)
        )

        time.sleep(2)

        lcd.clear()

        lcd.write_string(
            ' Ready to scan! '.center(16)
        )

    finally:

        is_processing = False


# ============================================================
# SHOW CHECKOUT TOTAL
# ============================================================

def show_checkout_total(lcd):
    """
    Calculates and displays the current cart total.
    """

    if not scanned_cart:

        lcd.clear()

        lcd.write_string(
            ' Cart is empty '.center(16)
        )

        lcd.cursor_pos = (1, 0)

        lcd.write_string(
            ' Nothing to pay '.center(16)
        )

        print(
            "[Checkout] Cart is empty."
        )

        time.sleep(2)

        return 0.0

    total = sum(
        float(item['price'])
        for item in scanned_cart
    )

    print()
    print("=" * 50)
    print("[CHECKOUT]")
    print(f"Items: {len(scanned_cart)}")
    print(f"TOTAL: EUR {total:.2f}")
    print("=" * 50)

    lcd.clear()

    lcd.write_string(
        ' CHECKOUT '.center(16)
    )

    lcd.cursor_pos = (1, 0)

    lcd.write_string(
        f"EUR {total:.2f}".center(16)
    )

    return total


# ============================================================
# CAMERA PRODUCT DETECTION
# ============================================================

def calculate_change_ratio(background_gray, current_gray):
    """
    Calculates how much of the ROI has changed compared
    with the empty background.
    """

    difference = cv2.absdiff(
        background_gray,
        current_gray
    )

    _, threshold = cv2.threshold(
        difference,
        25,
        255,
        cv2.THRESH_BINARY
    )

    # Remove small noise
    kernel = np.ones(
        (5, 5),
        np.uint8
    )

    threshold = cv2.morphologyEx(
        threshold,
        cv2.MORPH_OPEN,
        kernel
    )

    threshold = cv2.morphologyEx(
        threshold,
        cv2.MORPH_CLOSE,
        kernel
    )

    changed_pixels = cv2.countNonZero(
        threshold
    )

    total_pixels = threshold.shape[0] * threshold.shape[1]

    if total_pixels == 0:
        return 0.0

    return changed_pixels / total_pixels


def calculate_frame_difference(frame_a, frame_b):
    """
    Calculates how much two consecutive ROI frames differ.
    Used to determine whether the product has stopped moving.
    """

    difference = cv2.absdiff(
        frame_a,
        frame_b
    )

    _, threshold = cv2.threshold(
        difference,
        20,
        255,
        cv2.THRESH_BINARY
    )

    changed_pixels = cv2.countNonZero(
        threshold
    )

    total_pixels = threshold.shape[0] * threshold.shape[1]

    if total_pixels == 0:
        return 0.0

    return changed_pixels / total_pixels


def create_background(roi_gray_frames):
    """
    Creates a stable background image from several empty frames.
    Median filtering removes small camera/sensor noise.
    """

    stacked = np.stack(
        roi_gray_frames,
        axis=0
    )

    background = np.median(
        stacked,
        axis=0
    ).astype(np.uint8)

    background = cv2.GaussianBlur(
        background,
        (5, 5),
        0
    )

    return background


# ============================================================
# MAIN
# ============================================================

def main():

    global is_processing
    global scanned_cart

    print(
        "=== Smart Checkout AI System v9.0 ==="
    )

    print(
        "=== AI + CAMERA DETECTION + LCD + "
        "Audio + Voice + FINISH BUTTON ==="
    )

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

    pygame.mixer.init()

    # --------------------------------------------------------
    # ULTRASONIC SENSOR
    # --------------------------------------------------------
    # Kept connected as hardware, but it is no longer
    # responsible for detecting the product.
    # Camera detection is now the primary trigger.

    scanner = UltrasonicScanner(
        trigger_pin=23,
        echo_pin=24,
        threshold_cm=35.0
    )

    print(
        "[Hardware] HC-SR04 connected."
    )

    print(
        "[Hardware] Product detection: CAMERA"
    )

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    ai_engine = ObjectClassifier()

    # --------------------------------------------------------
    # RECEIPT MANAGER
    # --------------------------------------------------------

    receipt_mgr = ReceiptManager()

    # --------------------------------------------------------
    # BUZZER
    # --------------------------------------------------------

    checkout_buzzer = Buzzer(
        26,
        initial_value=False
    )

    checkout_buzzer.off()

    # --------------------------------------------------------
    # FINISH BUTTON
    # --------------------------------------------------------

    finish_button = Button(
        25,
        pull_up=True,
        bounce_time=0.25
    )

    print(
        "[Hardware] Finish button: GPIO25"
    )

    # --------------------------------------------------------
    # LCD
    # --------------------------------------------------------

    lcd = CharLCD(
        i2c_expander='PCF8574',
        address=0x27,
        port=1,
        cols=16,
        rows=2,
        dotsize=8
    )

    lcd.clear()

    lcd.write_string(
        ' SMART CHECKOUT '.center(16)
    )

    lcd.cursor_pos = (1, 0)

    lcd.write_string(
        ' System Online! '.center(16)
    )

    # --------------------------------------------------------
    # CAMERA
    # --------------------------------------------------------

    print(
        "[Camera] Starting Live Video Feed..."
    )

    picam2 = Picamera2()

    config = picam2.create_preview_configuration(
        main={
            "size": (640, 480),
            "format": "RGB888"
        }
    )

    picam2.configure(config)

    picam2.start()

    # Give camera time to stabilize
    time.sleep(2)

    # --------------------------------------------------------
    # ROI
    # --------------------------------------------------------

    box_width = 450
    box_height = 350
    
    roi_center_x = 240
    roi_center_y = 240

    # --------------------------------------------------------
    # CREATE INITIAL BACKGROUND
    # --------------------------------------------------------

    print()
    print(
        "[Camera] Creating empty-table background..."
    )

    print(
        "[Camera] Keep the scanning area EMPTY."
    )

    background_frames = []

    for i in range(15):

        startup_frame = picam2.capture_array()

        height, width, _ = startup_frame.shape

        top_left = (
            int(roi_center_x - box_width / 2),
            int(roi_center_y - box_height / 2)
        )

        bottom_right = (
            int(roi_center_x + box_width / 2),
            int(roi_center_y + box_height / 2)
        )

        startup_roi = startup_frame[
            top_left[1]:bottom_right[1],
            top_left[0]:bottom_right[0]
        ]

        startup_gray = cv2.cvtColor(
            startup_roi,
            cv2.COLOR_RGB2GRAY
        )

        startup_gray = cv2.GaussianBlur(
            startup_gray,
            (5, 5),
            0
        )

        background_frames.append(
            startup_gray
        )

        time.sleep(0.1)

    background_gray = create_background(
        background_frames
    )

    print(
        "[Camera] Background created successfully."
    )

    # --------------------------------------------------------
    # START MESSAGE
    # --------------------------------------------------------

    speak_bg(
        "Системата е готова за сканиране."
    )

    time.sleep(2)

    lcd.clear()

    lcd.write_string(
        ' Ready to scan! '.center(16)
    )

    print()
    print(
        "System online."
    )

    print(
        "Place products inside the green box."
    )

    print(
        "Camera-based product detection is active."
    )

    print(
        "Press physical FINISH button "
        "to complete checkout."
    )

    print(
        "Press 'q' only for emergency exit."
    )

    print()

    # --------------------------------------------------------
    # SCANNING SETTINGS
    # --------------------------------------------------------

    last_scan_time = 0

    cooldown_seconds = 6

    # Minimum percentage of ROI that must change
    # compared with the empty background.
    change_threshold = 0.025

    # Product must remain stable for this amount of time
    # before AI scanning starts.
    stable_time_required = 0.8

    # Maximum movement between two frames while deciding
    # that the object is stable.
    stability_threshold = 0.015

    # Candidate detection state
    candidate_start_time = None
    candidate_previous_gray = None

    # Used for controlled background updating
    background_update_alpha = 0.03

    # --------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------

    try:

        while True:

            # =================================================
            # FINISH BUTTON
            # =================================================

            if (
                finish_button.is_pressed
                and not is_processing
            ):

                print()
                print(
                    "[Button] FINISH button pressed."
                )

                # Show total
                total = show_checkout_total(
                    lcd
                )

                # Only finish if there are items
                if scanned_cart:

                    speak_bg(
                        f"Крайната сума е "
                        f"{total:.2f} евро."
                    )

                    time.sleep(2)

                    break

                else:

                    print(
                        "[Checkout] "
                        "Cannot finish empty cart."
                    )

                    continue

            # =================================================
            # CAMERA FRAME
            # =================================================

            frame_rgb = picam2.capture_array()

            height, width, _ = frame_rgb.shape

            # Display version
            # Picamera2 is already configured as RGB888,
            # so keep the same RGB image for display.
            frame = frame_rgb.copy()

            # =================================================
            # ROI
            # =================================================

            top_left = (
                int(roi_center_x - box_width / 2),
                int(roi_center_y - box_height / 2)
            )

            bottom_right = (
                int(roi_center_x + box_width / 2),
                int(roi_center_y + box_height / 2)
            )

            roi_rgb = frame_rgb[
                top_left[1]:bottom_right[1],
                top_left[0]:bottom_right[0]
            ]

            roi_gray = cv2.cvtColor(
                roi_rgb,
                cv2.COLOR_RGB2GRAY
            )

            roi_gray = cv2.GaussianBlur(
                roi_gray,
                (5, 5),
                0
            )

            current_time = time.time()

            time_since_last_scan = (
                current_time - last_scan_time
            )

            # =================================================
            # PROCESSING
            # =================================================

            if is_processing:

                cv2.rectangle(
                    frame,
                    top_left,
                    bottom_right,
                    (0, 0, 255),
                    4
                )

                cv2.putText(
                    frame,
                    "PROCESSING...",
                    (
                        top_left[0],
                        bottom_right[1] + 30
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 0, 255),
                    3
                )

                # Reset candidate detection while processing
                candidate_start_time = None
                candidate_previous_gray = None

            # =================================================
            # COOLDOWN
            # =================================================

            elif (
                time_since_last_scan
                < cooldown_seconds
            ):

                cv2.rectangle(
                    frame,
                    top_left,
                    bottom_right,
                    (0, 255, 255),
                    2
                )

                cv2.putText(
                    frame,
                    "WAIT...",
                    (
                        top_left[0],
                        bottom_right[1] + 30
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2
                )

                # Clear candidate detection
                candidate_start_time = None
                candidate_previous_gray = None

            # =================================================
            # READY
            # =================================================

            else:

                cv2.rectangle(
                    frame,
                    top_left,
                    bottom_right,
                    (0, 255, 0),
                    2
                )

                # -------------------------------------------------
                # CAMERA PRODUCT DETECTION
                # -------------------------------------------------

                change_ratio = calculate_change_ratio(
                    background_gray,
                    roi_gray
                )

                # -------------------------------------------------
                # OBJECT PRESENT
                # -------------------------------------------------

                if change_ratio > change_threshold:

                    # First frame where a product appears
                    if candidate_start_time is None:

                        candidate_start_time = current_time

                        candidate_previous_gray = (
                            roi_gray.copy()
                        )

                        print(
                            f"[Camera] Object detected "
                            f"(change: "
                            f"{change_ratio * 100:.1f}%)"
                        )

                    else:

                        frame_change = (
                            calculate_frame_difference(
                                candidate_previous_gray,
                                roi_gray
                            )
                        )

                        candidate_previous_gray = (
                            roi_gray.copy()
                        )

                        candidate_duration = (
                            current_time
                            - candidate_start_time
                        )

                        # -------------------------------------------------
                        # OBJECT IS STABLE
                        # -------------------------------------------------

                        if (
                            candidate_duration
                            >= stable_time_required
                            and frame_change
                            < stability_threshold
                        ):

                            print()
                            print(
                                "[Camera] Stable product detected!"
                            )

                            print(
                                f"[Camera] Background change: "
                                f"{change_ratio * 100:.1f}%"
                            )

                            print(
                                f"[Camera] Object stable for: "
                                f"{candidate_duration:.1f}s"
                            )

                            # Prevent another detection immediately
                            is_processing = True

                            last_scan_time = time.time()

                            # Reset candidate
                            candidate_start_time = None
                            candidate_previous_gray = None

                            # -----------------------------------------
                            # LCD
                            # -----------------------------------------

                            lcd.clear()

                            lcd.write_string(
                                ' Scanning... '.center(16)
                            )

                            # -----------------------------------------
                            # CAPTURE CLEAN FRAME
                            # -----------------------------------------

                            clean_frame_rgb = (
                                picam2.capture_array()
                            )

                            roi_frame = clean_frame_rgb[
                                top_left[1]:bottom_right[1],
                                top_left[0]:bottom_right[0]
                            ]

                            # -----------------------------------------
                            # AI THREAD
                            # -----------------------------------------

                            threading.Thread(
                                target=process_item_thread,
                                args=(
                                    roi_frame,
                                    ai_engine,
                                    checkout_buzzer,
                                    lcd
                                ),
                                daemon=True
                            ).start()

                # -------------------------------------------------
                # NO OBJECT
                # -------------------------------------------------

                else:

                    # Cancel an unfinished candidate
                    candidate_start_time = None
                    candidate_previous_gray = None

                    # Slowly adapt background to tiny changes
                    # in lighting/camera noise.
                    background_gray = cv2.addWeighted(
                        background_gray,
                        1.0 - background_update_alpha,
                        roi_gray,
                        background_update_alpha,
                        0
                    )

            # =================================================
            # DISPLAY INFORMATION
            # =================================================

            if (
                not is_processing
                and time_since_last_scan >= cooldown_seconds
            ):

                change_text = (
                    f"CHANGE: "
                    f"{change_ratio * 100:.1f}%"
                )

                cv2.putText(
                    frame,
                    change_text,
                    (
                        top_left[0],
                        top_left[1] - 15
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

            # =================================================
            # DISPLAY
            # =================================================

            display_frame = frame[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

            cv2.imshow(
                "Smart Checkout UI",
                display_frame
            )

            # =================================================
            # EMERGENCY EXIT
            # =================================================

            if (
                cv2.waitKey(1) & 0xFF
                == ord('q')
            ):

                print(
                    "\n[System] Emergency exit "
                    "requested with Q."
                )

                break

    except KeyboardInterrupt:

        print(
            "\n[System] Keyboard interrupt."
        )

    finally:

        print()

        print(
            "[System] Session ending..."
        )

        # ----------------------------------------------------
        # CAMERA CLEANUP
        # ----------------------------------------------------

        picam2.stop()

        cv2.destroyAllWindows()

        # ----------------------------------------------------
        # BUTTON CLEANUP
        # ----------------------------------------------------

        finish_button.close()

        # ----------------------------------------------------
        # BUZZER CLEANUP
        # ----------------------------------------------------

        checkout_buzzer.close()

        # ----------------------------------------------------
        # FINAL CHECKOUT
        # ----------------------------------------------------

        if scanned_cart:

            total = sum(
                float(item['price'])
                for item in scanned_cart
            )

            print()

            print(
                f"[System] Final total: "
                f"EUR {total:.2f}"
            )

            lcd.clear()

            lcd.write_string(
                ' Printing... '.center(16)
            )

            lcd.cursor_pos = (1, 0)

            lcd.write_string(
                f"EUR {total:.2f}".center(16)
            )

            speak_bg(
                "Процесът приключи. "
                "Принтирам касова бележка."
            )

            # Generate receipt
            receipt_mgr.generate_receipt(
                scanned_cart
            )

            time.sleep(3)

        else:

            print(
                "[System] No products "
                "were scanned."
            )

            lcd.clear()

            lcd.write_string(
                ' No items '.center(16)
            )

        # ----------------------------------------------------
        # OFFLINE
        # ----------------------------------------------------

        lcd.clear()

        lcd.write_string(
            ' System Offline '.center(16)
        )

        print()

        print(
            "[System] Checkout completed."
        )

        print(
            "Goodbye!"
        )


# ============================================================
# PROGRAM ENTRY
# ============================================================

if __name__ == "__main__":
    main()
