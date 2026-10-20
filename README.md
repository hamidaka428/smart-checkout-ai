# Smart Checkout AI

An autonomous self-checkout prototype built with **Raspberry Pi 5**, computer vision, and Edge AI.

The system uses a camera to detect products, classifies them with a TensorFlow Lite model, retrieves product information from a local PHP API, and displays the product name and price on an LCD. It also provides Bulgarian voice feedback, adds recognised products to the cart, and generates a receipt when checkout is completed.

## Demo

[**▶ Watch the Smart Checkout AI demo**](https://youtu.be/6w_1xqbzkQ8)

## Features

- **Camera-based detection** — compares camera frames with a background reference to detect a newly placed object.
- **On-device classification** — TensorFlow Lite model with 15 product classes and 224 × 224 input images.
- **Confidence threshold** — predictions below the configured 85% threshold are rejected.
- **Live feedback** — 16 × 2 I²C LCD, buzzer, and Bulgarian text-to-speech prompts generated at runtime with gTTS. Audio files are cached locally after generation; pre-generated voice files are not included in the repository.
- **Checkout flow** — recognised products are added to the cart; the physical Finish button completes the session.
- **Receipt generation** — generates a text receipt with subtotal, VAT, and total.
- **Product backend** — PHP endpoints and MariaDB support product lookup and order storage.
- **Dataset tools** — scripts for collecting labelled images using the camera.

## Hardware

| Component | Connection / role |
|---|---|
| Raspberry Pi 5 | Main computing platform |
| Raspberry Pi Camera Module 3 | CSI camera |
| HC-SR04 ultrasonic sensor | Trigger: GPIO 23, Echo: GPIO 24 |
| 16 × 2 LCD with PCF8574 I²C backpack | I²C bus 1, address `0x27` |
| Buzzer | GPIO 26 |
| Finish button | GPIO 25, internal pull-up |

**Note:** product detection is camera-based in the current application. The HC-SR04 is initialised as part of the hardware setup, but it is not the primary product-detection trigger.

## How It Works

1. **Initialisation** — the application starts the model, camera, and hardware components.
2. **Background reference** — several frames of the empty scanning area are captured.
3. **Object detection** — the current camera frame is compared with the background.
4. **Stability check** — the object must remain sufficiently stable before classification starts.
5. **AI classification** — the image region is passed to the TensorFlow Lite model.
6. **Product lookup** — the predicted label is used to retrieve product details from the local PHP API.
7. **Checkout** — the LCD, buzzer, and voice prompt provide feedback; the Finish button completes the session and triggers receipt/order handling.

## Recognised Product Classes

The model contains 15 classes:

- 9V battery (`RPI_BATTERY_9V`)
- Breadboard (`RPI_BREADBOARD`)
- Cable (`RPI_CABLE`)
- GPIO extension board (`RPI_EXTENSION`)
- Flashlight (`RPI_FLASHLIGHT`)
- Joystick (`RPI_JOYSTICK`)
- Keyboard (`RPI_KBOARD`)
- DC motor (`RPI_MOTOR`)
- Mouse (`RPI_MOUSE`)
- Multimeter (`RPI_MULTIMETER`)
- Phone (`RPI_PHONE`)
- Raspberry Pi (`RPI_RASPBERRY`)
- Scissors (`RPI_SCISSORS`)
- Servo (`RPI_SERVO`)
- Stepper motor (`RPI_STEPPER`)

The repository includes the trained TensorFlow Lite model, its label file, and a small sample of the image dataset. The full training dataset is not included.

## Project Structure

```text
smart-checkout-ai/
├── main.py
├── ai/
│   ├── classifier.py
│   └── model/
│       ├── model_unquant.tflite
│       └── labels.txt
├── hardware/
│   └── sensor.py
├── utils/
│   └── receipt.py
├── backend/
│   ├── api.php
│   ├── save_order.php
│   ├── dashboard.php
│   ├── db.php
│   ├── config.php
│   ├── config.local.php.example
│   └── schema.sql
├── dataset_sample/
├── docs/
│   └── sample_receipt.txt
├── collect_data.py
├── auto_collect.py
├── test_ai.py
├── requirements.txt
└── .gitignore
```

## Requirements

- Raspberry Pi OS on Raspberry Pi 5
- Python version and packages compatible with the installed Raspberry Pi OS
- Raspberry Pi camera support (`Picamera2` / `libcamera`)
- OpenCV
- TensorFlow Lite runtime compatible with the environment
- GPIO Zero and the required GPIO/I²C libraries
- PHP and MariaDB for the backend

The exact package versions and availability can vary by Raspberry Pi OS and Python version. Check `requirements.txt` and the Raspberry Pi OS packages before installing.

## Installation

Enable the camera and I²C interfaces on the Raspberry Pi first.

Install the system packages used by the camera and OpenCV:

```bash
sudo apt update
sudo apt install python3-picamera2 python3-opencv
```

Clone the repository:

```bash
git clone https://github.com/hamidaka428/smart-checkout-ai.git
cd smart-checkout-ai
```

Create a virtual environment that can access system-installed packages such as Picamera2:

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set up the PHP/MariaDB backend by following [`backend/README.md`](backend/README.md). Configure database credentials locally before starting the full checkout workflow.

## Usage

Run the camera/model test:

```bash
python test_ai.py
```

Start the application:

```bash
python main.py
```

Place one product in the camera's scanning area. Press the physical **Finish** button to complete checkout. Press `q` to exit the camera window.

## Collecting Training Data

Two scripts are included for collecting labelled images:

```bash
python collect_data.py
python auto_collect.py
```

Review the configuration and on-screen instructions in each script before use.

## Backend

The backend provides product lookup, order saving, and a dashboard. See [`backend/README.md`](backend/README.md) and [`backend/schema.sql`](backend/schema.sql) for setup details.

Do not commit real database passwords or other secrets. Use local configuration for credentials and keep it out of version control.

## Limitations and Future Improvements

- The classifier recognises only the 15 classes represented in its training data.
- Adding product classes requires collecting labelled images and retraining the model.
- Bulgarian voice prompts are generated at runtime with gTTS. The first generation of a phrase requires an internet connection; generated MP3 files are cached locally and are not included in the repository.
- Potential improvements include model quantisation, support for multiple products in a frame, and moving configuration values into a separate configuration file.

## License

This project is available for personal, educational, research, and other non-commercial use under the [Non-Commercial Source Code License](LICENSE).

You may copy, modify, and share the project for non-commercial purposes, provided you retain the license and copyright notice and identify your changes. Commercial use, sale, or inclusion in a paid product or service requires prior written permission from the author.

Third-party components remain subject to their own licenses.
