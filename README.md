# See No Evil: Semantic Context-Aware Privacy Risk Detection for AR

## Introduction
This repository contains the official implementation of the paper **"SEE NO EVIL: SEMANTIC CONTEXT-AWARE PRIVACY RISK DETECTION FOR AR"** (Accepted by **ICASSP 2026**).

**PrivAR** is a privacy-preserving framework designed for Augmented Reality (AR) systems. It addresses the "always-on" sensing privacy risks by leveraging Vision Language Models (VLMs) with Chain-of-Thought (CoT) prompting.

### Key Features:
* **Context-Aware Risk Detection:** Uses visual scene cues to infer potential sensitive information (e.g., identifying password notes in an office setting) rather than relying solely on object categories.
* **Privacy-Preserving Obfuscation:** Implements a "text obfuscation first" pipeline at the edge server using the EAST text detection model and a combination of Gaussian blur and elastic deformation. This prevents the VLM provider from accessing raw sensitive text.
* **Warning Interfaces:** Provides contextually-informed warning modes (Center-screen, Top-screen, Region Overlay) to enhance user privacy awareness in AR.

![System Architecture](https://github.com/jlliu2001/AR-Privacy-Detection/raw/main/docs/system_PrivAR.png)

## 📱 Quick Demo (Pre-built APK)

For a quick demonstration of **PrivAR** without setting up the full development environment, we provide a pre-built Android APK file. You can install it directly on your mobile device to test the functionality.

[**⬇️ Download PrivAR.apk**](https://drive.google.com/file/d/1CfvoSniGNr0KZw8B96h7xxHZ8IkoQW6k/view?usp=sharing)

**Installation Steps:**
1.  Download the `.apk` file to your Android device.
2.  Install the application (you may need to enable **"Install from Unknown Sources"** in your device settings).
3.  Launch the app and grant the necessary **Camera permissions** to enable AR sensing capabilities.

## 🛠️ Prerequisites

### Unity Environment
* **Unity Version:** `2022.3.6f1`
* **Target Platform:** Android / iOS (AR Mobile)

### Python Environment
* **Python Version:** `3.7+`
* **Dependencies:**
    The core functionality (Edge Server processing and Cloud VLM inference) requires the following libraries.
    ```
    numpy
    opencv-python
    scipy
    openai
    requests
    flask
    pytesseract
    subprocess
    ```
## 🚀 Installation & Usage
### 1. Python Server Setup
Ensure your Python environment is ready and dependencies are installed.

* Clone this repository.
* Navigate to the python script directory.
* Set up your OpenAI API Key in the configuration file or environment variable (for GPT-4o-mini inference).


### 2. Unity Project Setup
To integrate PrivAR into your Unity AR project, follow these steps:

#### Create New Project:

* Open Unity Hub.
* Create a new project using the AR Mobile template.


#### Import Scripts:

* Navigate to your Unity project's assets folder: your_repo/Assets/MobileARTemplateAssets/
* Create a new folder named Scripts.
* Copy ARPrivacyMonitorHttp.cs and privacy_http_server.py files from this repository into: your_repo/Assets/MobileARTemplateAssets/Scripts/

#### Import Prefabs:

* Navigate to your_repo/Assets/MobileARTemplateAssets/
* Locate the existing Prefabs folder (or create it if it doesn't exist).
* Copy the contents of the Prefabs folder from this repository into: your_repo/Assets/MobileARTemplateAssets/Prefabs/

#### Final Configuration:

Follow the detailed step-by-step configuration guide in ./docs/PrivAR_readme.pdf  to wire up the UI components and connect the AR Camera to the Python backend.

## 📂 Dataset
This repository includes the dataset collected for the PrivAR evaluation (Section 3.1 of the paper), covering:

* **Scenes:** The data covers 4 diverse indoor environments:
    * Office
    * Living Room
    * Dorm
    * Buffet
* **Virtual Objects:** Includes 6 types of virtual objects used in AR interactions:
    * Coffee Cup
    * Whiteboard
    * Indoor Plant
    * Guitar
    * Vase
    * Chair
* **Sensitive Information (5 Types):**
    * ID Cards
    * Credit Cards
    * Handwritten Password Notes
    * Text displayed on Computer Screens
    * Text displayed on Phone Screens
* **Multi-Instance Complexity:** **40.63%** of the positive samples contain multiple co-occurring sensitive items (e.g., a handwritten password note appearing alongside a transcript), requiring the model to handle complex scenes.
* **Negative Samples (Hard Negatives):** To evaluate robustness, the dataset includes **94 visually similar but non-sensitive negative samples**, such as published academic papers and coupons, which share visual characteristics with sensitive documents but should not trigger privacy alerts.


## 🔗 Citation
If you find this work useful in your research, please consider citing our paper:

