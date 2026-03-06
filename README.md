# PrivAR

This repository accompanies the paper **"See no evil: Semantic context-aware privacy risk detection for AR"** to appear at IEEE ICASSP 2026.

<img src="/docs/system_PrivAR.png" width="600">

## 🛠️ Prerequisites

### Unity Environment
* **Unity Version:** `2022.3.6f1`
* **Target Platform:** Android / iOS (AR Mobile)

### Python Environment
* **Python Version:** `3.7+`
* **Dependencies:**
    The core functionality (Edge Server processing and Cloud VLM inference) requires the following libraries.
    ```
    numpy, opencv-python, scipy, openai, requests, flask, pytesseract, subprocess
    ```
## 🚀 Installation & Usage
### 1. Python Server Setup

* Navigate to the Python script directory.
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

